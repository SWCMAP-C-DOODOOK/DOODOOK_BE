# moved from apps/common/views/ocr.py
import io
import json
import os

from django.conf import settings
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import OcrApproval, OcrValidationLog, Transaction
from apps.common.permissions import IsAdminOrReadOnly, IsAdminRole
from apps.ocr.serializers import OcrApprovalSerializer, ReceiptOCRRequestSerializer
from apps.ocr.services import OCRServiceError, encode_file_to_base64
from apps.ocr.services.clova_ocr import extract_text_clova, parse_receipt


class ReceiptOCRView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        for key in ("transaction_id", "store", "overwrite", "manual_overrides", "notes"):
            if key not in data and key in request.query_params:
                data[key] = request.query_params[key]

        uploaded_image = request.FILES.get("image")
        has_image = bool(uploaded_image)
        serializer = ReceiptOCRRequestSerializer(data=data, context={"has_image": has_image})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        transaction = None
        transaction_id = validated.get("transaction_id")
        store = validated.get("store", False)
        overwrite = validated.get("overwrite", False)
        manual_overrides = validated.get("manual_overrides") or {}
        notes = validated.get("notes", "")
        source = "uploaded" if has_image else "transaction"

        image_file = validated.get("image") or uploaded_image
        if image_file and hasattr(image_file, "size") and image_file.size == 0:
            raise ValidationError({"image": "Empty image file"})
        if image_file:
            content_type = getattr(image_file, "content_type", "") or ""
            if content_type and not content_type.startswith("image/"):
                raise ValidationError({"image": "Only image files are supported"})

        if transaction_id:
            transaction = get_object_or_404(Transaction.objects.select_related("user"), pk=transaction_id)
            if not has_image:
                if not transaction.receipt_image:
                    return Response({"detail": "Receipt image not found for transaction"}, status=status.HTTP_400_BAD_REQUEST)
                image_file = transaction.receipt_image
                source = "transaction"

        if image_file is None:
            raise ValidationError({"detail": "Image source not found"})

        needs_close = False
        if hasattr(image_file, "open") and getattr(image_file, "closed", True):
            image_file.open("rb")
            needs_close = True

        image_name = getattr(image_file, "name", "") or ""
        image_format = os.path.splitext(image_name)[1].lower().lstrip(".") or "jpg"

        raw_payload = None

        try:
            clova_url = os.environ.get("CLOVA_OCR_API_URL") or getattr(settings, "CLOVA_OCR_API_URL", "")
            clova_secret = os.environ.get("CLOVA_OCR_SECRET") or getattr(settings, "CLOVA_OCR_SECRET", "")
            if not clova_url or not clova_secret:
                raise ValidationError({"detail": "Clova OCR environment not configured"})
            b64_content = encode_file_to_base64(image_file)
            response_payload = extract_text_clova(
                b64_content,
                api_url=clova_url,
                secret=clova_secret,
                image_format=image_format,
            )
            raw_text = response_payload.get("text", "")
            raw_payload = response_payload.get("raw")
        except OCRServiceError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)
        finally:
            if needs_close and hasattr(image_file, "close"):
                image_file.close()

        parsed_fields = parse_receipt(raw_text)

        final_fields = parsed_fields.copy()
        for key, value in manual_overrides.items():
            if key not in final_fields:
                continue
            if key == "amount":
                try:
                    final_fields[key] = int(str(value).replace(",", ""))
                except (TypeError, ValueError):
                    continue
            else:
                final_fields[key] = value

        is_valid = bool(final_fields.get("amount") and final_fields.get("date"))

        stored = False
        if store:
            if not transaction:
                return Response({"detail": "transaction_id is required to store OCR text"}, status=status.HTTP_400_BAD_REQUEST)
            is_admin_role = getattr(request.user, "role", None) == "admin" or getattr(request.user, "is_staff", False)
            if not (is_admin_role or transaction.user_id == request.user.id):
                return Response({"detail": "Not authorized to store OCR result"}, status=status.HTTP_403_FORBIDDEN)
            if transaction.ocr_text and not overwrite:
                return Response({"detail": "OCR text already exists. Pass overwrite=true to replace."}, status=status.HTTP_409_CONFLICT)

            with db_transaction.atomic():
                transaction.ocr_text = json.dumps(
                    {
                        "raw_text": raw_text,
                        "fields": final_fields,
                        "raw_response": raw_payload,
                    },
                    ensure_ascii=False,
                )
                transaction.save(update_fields=["ocr_text", "updated_at"])
                approval, _created = OcrApproval.objects.get_or_create(transaction=transaction)
                approval.status = OcrApproval.Status.PENDING
                approval.reviewer = None
                approval.decided_at = None
                approval.notes = ""
                approval.save(update_fields=["status", "reviewer", "decided_at", "notes", "updated_at"])
            stored = True

        if transaction:
            OcrValidationLog.objects.create(
                transaction=transaction,
                user=request.user,
                extracted_json={
                    "raw_text": raw_text,
                    "parsed": parsed_fields,
                    "final": final_fields,
                    "manual_overrides": manual_overrides,
                    "raw_response": raw_payload,
                },
                is_valid=is_valid,
                notes=notes or "",
            )

        return Response(
            {
                "transaction_id": transaction_id,
                "text": raw_text,
                "fields": final_fields,
                "stored": stored,
                "source": source,
                "raw_response": raw_payload,
            },
            status=status.HTTP_200_OK,
        )


class _OcrApprovalMixin(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    target_status = None

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["status"] = self.target_status
        serializer = OcrApprovalSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        approval, _created = OcrApproval.objects.get_or_create(transaction=transaction)
        approval.mark(
            reviewer=request.user,
            status=self.target_status,
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(
            {
                "transaction_id": transaction.id,
                "status": approval.status,
                "notes": approval.notes,
                "decided_at": approval.decided_at,
            },
            status=status.HTTP_200_OK,
        )


class OcrApproveView(_OcrApprovalMixin):
    target_status = OcrApproval.Status.APPROVED


class OcrRejectView(_OcrApprovalMixin):
    target_status = OcrApproval.Status.REJECTED

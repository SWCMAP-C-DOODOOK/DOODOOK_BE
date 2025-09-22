# moved from apps/common/views.py
import os

from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Transaction
from apps.common.serializers import ReceiptOCRRequestSerializer
from apps.common.services.ocr import OCRServiceError, extract_text_from_image


class ReceiptOCRView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        for key in ("transaction_id", "store", "overwrite"):
            if key not in data and key in request.query_params:
                data[key] = request.query_params[key]

        has_image = bool(request.FILES.get("image"))
        serializer = ReceiptOCRRequestSerializer(data=data, context={"has_image": has_image})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        transaction = None
        transaction_id = validated.get("transaction_id")
        store = validated.get("store", False)
        overwrite = validated.get("overwrite", False)
        source = "uploaded" if has_image else "transaction"

        image_file = None
        if has_image:
            image_file = request.FILES.get("image")
            content_type = getattr(image_file, "content_type", "") or ""
            if content_type and not content_type.startswith("image/"):
                raise ValidationError({"image": "Only image files are supported"})
            if hasattr(image_file, "size") and image_file.size == 0:
                raise ValidationError({"image": "Empty image file"})

        if transaction_id:
            transaction = get_object_or_404(Transaction.objects.select_related("user"), pk=transaction_id)
            if not has_image:
                if not transaction.receipt_image:
                    return Response({"detail": "Receipt image not found for transaction"}, status=status.HTTP_400_BAD_REQUEST)
                image_file = transaction.receipt_image
                source = "transaction"

        if image_file is None:
            raise ValidationError({"detail": "Image source not found"})

        api_key = os.environ.get("KAKAO_REST_API_KEY", "")

        needs_close = False
        if hasattr(image_file, "open") and getattr(image_file, "closed", True):
            image_file.open("rb")
            needs_close = True

        try:
            text = extract_text_from_image(image_file, api_key)
        except OCRServiceError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)
        finally:
            if needs_close and hasattr(image_file, "close"):
                image_file.close()

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
                transaction.ocr_text = text
                transaction.save(update_fields=["ocr_text", "updated_at"])
            stored = True
            # TODO: leverage IsOwnerOrAdmin permission for store workflow to centralize checks

        return Response(
            {
                "transaction_id": transaction_id,
                "text": text,
                "stored": stored,
                "source": source,
            },
            status=status.HTTP_200_OK,
        )

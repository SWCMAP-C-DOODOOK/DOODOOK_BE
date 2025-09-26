from calendar import monthrange
from datetime import date

from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Transaction


class CategoryShareStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        if not start or not end:
            return Response({"detail": "start and end are required as YYYY-MM"}, status=400)

        try:
            start_year, start_month = [int(part) for part in start.split("-")]
            end_year, end_month = [int(part) for part in end.split("-")]
            start_date = date(start_year, start_month, 1)
            end_date = date(end_year, end_month, 1)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid start/end format"}, status=400)

        end_last_day = monthrange(end_year, end_month)[1]
        end_date_exclusive = date(end_year, end_month, end_last_day) + date.resolution

        queryset = (
            Transaction.objects.filter(
                user=request.user,
                type=Transaction.TransactionType.EXPENSE,
                date__gte=start_date,
                date__lt=end_date_exclusive,
            )
            .values("category")
            .annotate(total=Sum("amount"))
            .order_by("category")
        )

        total_amount = sum(item["total"] or 0 for item in queryset)
        results = []
        for item in queryset:
            category = item["category"] or "Uncategorized"
            amount = int(item["total"] or 0)
            percent = (amount / total_amount * 100) if total_amount else 0
            results.append({"category": category, "amount": amount, "percent": round(percent, 2)})

        return Response({"start": start, "end": end, "total": total_amount, "items": results})


class AccumulatedStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        granularity = request.query_params.get("granularity", "month")
        if granularity not in {"month", "day"}:
            return Response({"detail": "granularity must be month or day"}, status=400)

        trunc = TruncMonth if granularity == "month" else TruncDay

        incomes = (
            Transaction.objects.filter(user=request.user, type=Transaction.TransactionType.INCOME)
            .annotate(period=trunc("date"))
            .values("period")
            .annotate(total=Sum("amount"))
            .order_by("period")
        )

        expenses = (
            Transaction.objects.filter(user=request.user, type=Transaction.TransactionType.EXPENSE)
            .annotate(period=trunc("date"))
            .values("period")
            .annotate(total=Sum("amount"))
            .order_by("period")
        )

        income_running, expense_running = 0, 0
        income_results, expense_results = [], []

        for item in incomes:
            income_running += int(item["total"] or 0)
            income_results.append({"period": item["period"].date(), "cumulative": income_running})

        for item in expenses:
            expense_running += int(item["total"] or 0)
            expense_results.append({"period": item["period"].date(), "cumulative": expense_running})

        return Response(
            {
                "granularity": granularity,
                "income": income_results,
                "expense": expense_results,
            }
        )

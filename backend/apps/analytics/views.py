"""Analytics endpoints.

Read-only by design: nothing here writes, and every response is scoped to the
requesting user through the same per-user queryset the rest of the API uses.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class AnalyticsViewSet(viewsets.ViewSet):
    """Spending analytics for the authenticated user.

    Registered as a viewset so the endpoints live under one prefix and show up in
    the browsable API, even though there are no models behind it.
    """

    def _currency(self, request):
        return services.resolve_currency(request.query_params.get("currency"))

    def _months(self, request, default=services.DEFAULT_TREND_MONTHS):
        raw = request.query_params.get("months", default)
        try:
            months = int(raw)
        except (TypeError, ValueError):
            raise services.AnalyticsError("`months` must be an integer.")
        return max(3, min(months, 120))

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """Everything the spending dashboard needs, in one request.

        Query parameters: `currency` (defaults to the principal currency) and
        `months` (trend window length, 3–120).
        """
        try:
            payload = services.build_dashboard(
                request.user,
                currency_code=request.query_params.get("currency"),
                months=self._months(request),
            )
        except services.AnalyticsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="period")
    def period(self, request):
        """Totals and categories for one period, compared with the previous one.

        Query parameters: `granularity` (`month` | `quarter` | `year`), `anchor`
        (`YYYY-MM`, `YYYY-QN` or `YYYY`), `currency`.
        """
        granularity = request.query_params.get("granularity", "month")
        anchor = request.query_params.get("anchor") or None
        try:
            currency = self._currency(request)
            current, previous, same_period_last_year = services.resolve_period(
                granularity, anchor, None
            )
        except services.AnalyticsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        current_totals = services.period_totals(
            request.user, currency, current.start, current.end
        )
        previous_totals = services.period_totals(
            request.user, currency, previous.start, previous.end
        )
        last_year_totals = services.period_totals(
            request.user, currency, same_period_last_year.start, same_period_last_year.end
        )

        return Response(
            {
                "currency": currency.code,
                "period": {
                    **current.as_dict(),
                    "compared_with": previous.as_dict(),
                    "same_period_last_year": same_period_last_year.as_dict(),
                },
                "totals": {
                    "current": services._totals_payload(current_totals),
                    "previous": services._totals_payload(previous_totals),
                    "same_period_last_year": services._totals_payload(last_year_totals),
                },
                "comparisons": {
                    "consumption": services.delta(
                        current_totals["consumption"], previous_totals["consumption"]
                    ),
                    "income": services.delta(
                        current_totals["income"], previous_totals["income"]
                    ),
                    "consumption_vs_last_year": services.delta(
                        current_totals["consumption"], last_year_totals["consumption"]
                    ),
                },
                "categories": services.category_breakdown(
                    request.user, currency, current.start, current.end
                ),
                "previous_categories": services.category_breakdown(
                    request.user, currency, previous.start, previous.end
                ),
            }
        )

    @action(detail=False, methods=["get"], url_path="trend")
    def trend(self, request):
        """Monthly income/consumption series, for the trend chart."""
        try:
            currency = self._currency(request)
        except services.AnalyticsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        months = self._months(request)
        return Response(
            {
                "currency": currency.code,
                "months": months,
                "series": services.monthly_series(request.user, currency, months),
            }
        )

    @action(detail=False, methods=["get"], url_path="categories")
    def categories(self, request):
        """Per-category consumption over time, for a stacked view."""
        try:
            currency = self._currency(request)
        except services.AnalyticsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        months = self._months(request)
        payload = services.category_series(request.user, currency, months)
        payload["currency"] = currency.code
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="recurring")
    def recurring(self, request):
        """Costs that repeat nearly every month with little variation."""
        try:
            currency = self._currency(request)
        except services.AnalyticsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "currency": currency.code,
                "recurring": services.recurring_expenses(request.user, currency, months=12),
            }
        )


class SpendingView(APIView):
    """Current-month outlook: pace, projection and how it compares with normal."""

    def get(self, request):
        try:
            currency = services.resolve_currency(request.query_params.get("currency"))
        except services.AnalyticsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"currency": currency.code, **services.spend_outlook(request.user, currency)}
        )

"""Operational models: an audit trail and a kill switch for console actions."""

from django.conf import settings
from django.db import models


class OperationRun(models.Model):
    """One invocation of a maintenance operation, successful or not.

    Every action triggered from the superuser console is recorded here, including
    who ran it, with what arguments and what came back. Console actions mutate
    shared data or restart background work, so "who did that, and when" must be
    answerable without going to the server logs.
    """

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    operation = models.CharField(max_length=64, db_index=True)
    arguments = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RUNNING, db_index=True
    )
    # `SET_NULL` keeps the history if the operator's account is later deleted.
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operation_runs",
    )
    output = models.TextField(blank=True, default="")
    error = models.TextField(blank=True, default="")
    result = models.JSONField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "operation run"
        verbose_name_plural = "operation runs"
        indexes = [models.Index(fields=["operation", "-started_at"])]

    def __str__(self) -> str:
        return f"{self.operation} [{self.status}] {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def succeeded(self) -> bool:
        return self.status == self.Status.SUCCESS


class OpsSettings(models.Model):
    """Singleton row holding console switches.

    A model rather than a settings constant so an operator can flip a switch at
    runtime (a deploy is not always possible when something is on fire). The
    safety-critical default is "everything off that could hurt".
    """

    #: Allow maintenance operations that change data to be started from the API.
    allow_mutating_operations = models.BooleanField(
        default=True,
        help_text=(
            "When off, only read-only operations (checks, statistics) may be run "
            "from the console."
        ),
    )
    #: Schema changes from a web button are opt-in; the CLI is always available.
    allow_destructive_operations = models.BooleanField(
        default=False,
        help_text="Required for operations such as running migrations from the console.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "operations settings"
        verbose_name_plural = "operations settings"

    def __str__(self) -> str:
        return "Operations settings"

    def save(self, *args, **kwargs):
        # Force a single row: the console reads it with `load()`.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "OpsSettings":
        """Return the singleton, creating it on first use."""
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

from fluent.handler import FluentRecordFormatter


class CustomFluentRecordFormatter(FluentRecordFormatter):
    def format(self, record):
        # Capture existing fields from the base formatter
        base_record = super().format(record)
        skip_list = (
            # "asctime",
            # "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "id",
            # "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "msecs",
            "message",
            "msg",
            # "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "extra",
            "auth_token",
            "password",
            "stack_info",
            "sys_host",
            "sys_name",
            "sys_module",
        )

        # Include any additional `extra` fields
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if (key not in base_record and key not in skip_list)
        }
        base_record.update(extra)
        return base_record

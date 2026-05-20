from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Iterator, List, Optional


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class LogLevel(str, Enum):
    TRACE    = "TRACE"
    DEBUG    = "DEBUG"
    INFO     = "INFO"
    NOTICE   = "NOTICE"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"
    UNKNOWN  = "UNKNOWN"

    @classmethod
    def from_str(cls, raw: str) -> "LogLevel":
        mapping = {
            "trace": cls.TRACE,
            "debug": cls.DEBUG,
            "info": cls.INFO,
            "notice": cls.NOTICE,
            "warn": cls.WARNING,
            "warning": cls.WARNING,
            "error": cls.ERROR,
            "err": cls.ERROR,
            "critical": cls.CRITICAL,
            "crit": cls.CRITICAL,
            "fatal": cls.CRITICAL,
            "emerg": cls.CRITICAL,
            "alert": cls.CRITICAL,
        }
        return mapping.get(raw.lower(), cls.UNKNOWN)


@dataclass
class LogEntry:
    raw_line: str
    timestamp: Optional[datetime] = None
    level: LogLevel = LogLevel.UNKNOWN
    source: Optional[str] = None        # host, service, logger name
    message: str = ""
    stack_trace: Optional[str] = None   # stitched multi-line
    extra: Dict[str, str] = field(default_factory=dict)
    format_detected: str = "unknown"


# ---------------------------------------------------------------------------
# Per-format parsers
# ---------------------------------------------------------------------------

_TS_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S,%f",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%d/%b/%Y:%H:%M:%S %z",
    "%b %d %H:%M:%S",
]


def _parse_timestamp(raw: str) -> Optional[datetime]:
    raw = raw.strip()
    for fmt in _TS_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


# --- JSON ---

def _try_json(line: str) -> Optional[LogEntry]:
    if not line.startswith("{"):
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    level_raw = (
        obj.get("level") or obj.get("severity") or
        obj.get("log_level") or obj.get("lvl") or ""
    )
    msg = (
        obj.get("message") or obj.get("msg") or
        obj.get("text") or obj.get("log") or line
    )
    ts_raw = (
        obj.get("timestamp") or obj.get("time") or
        obj.get("@timestamp") or obj.get("ts") or ""
    )
    return LogEntry(
        raw_line=line,
        timestamp=_parse_timestamp(str(ts_raw)) if ts_raw else None,
        level=LogLevel.from_str(str(level_raw)),
        source=obj.get("logger") or obj.get("service") or obj.get("host"),
        message=str(msg),
        extra={k: str(v) for k, v in obj.items() if k not in {"message", "msg", "level", "timestamp", "time"}},
        format_detected="json",
    )


# --- Nginx / Apache Combined ---
_NGINX_RE = re.compile(
    r'(?P<remote_addr>\S+)\s+-\s+(?P<remote_user>\S+)\s+'
    r'\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<proto>[^"]+)"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\d+|-)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)")?'
)

def _try_nginx(line: str) -> Optional[LogEntry]:
    m = _NGINX_RE.match(line)
    if not m:
        return None
    status = int(m.group("status"))
    level = (
        LogLevel.ERROR if status >= 500 else
        LogLevel.WARNING if status >= 400 else
        LogLevel.INFO
    )
    return LogEntry(
        raw_line=line,
        timestamp=_parse_timestamp(m.group("time")),
        level=level,
        source=m.group("remote_addr"),
        message=f'{m.group("method")} {m.group("path")} → {status}',
        extra={
            "status": str(status),
            "bytes": m.group("bytes"),
            "user_agent": m.group("ua") or "",
            "referer": m.group("referer") or "",
        },
        format_detected="nginx",
    )


# --- RFC 5424 Syslog ---
_SYSLOG5424_RE = re.compile(
    r'<(?P<pri>\d+)>(?P<version>\d)\s+'
    r'(?P<timestamp>\S+)\s+(?P<hostname>\S+)\s+'
    r'(?P<appname>\S+)\s+(?P<procid>\S+)\s+(?P<msgid>\S+)\s+'
    r'(?P<structured>-|\[.*?\])\s*(?P<msg>.*)',
    re.DOTALL,
)
_SYSLOG3164_RE = re.compile(
    r'(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<host>\S+)\s+(?P<prog>[^\[:\s]+)(?:\[(?P<pid>\d+)\])?:\s+(?P<msg>.*)'
)

_PRIORITY_LEVEL = {
    0: LogLevel.CRITICAL, 1: LogLevel.CRITICAL, 2: LogLevel.CRITICAL,
    3: LogLevel.ERROR,    4: LogLevel.WARNING,   5: LogLevel.NOTICE,
    6: LogLevel.INFO,     7: LogLevel.DEBUG,
}

def _try_syslog(line: str) -> Optional[LogEntry]:
    m5 = _SYSLOG5424_RE.match(line)
    if m5:
        pri = int(m5.group("pri")) % 8
        return LogEntry(
            raw_line=line,
            timestamp=_parse_timestamp(m5.group("timestamp")),
            level=_PRIORITY_LEVEL.get(pri, LogLevel.UNKNOWN),
            source=f'{m5.group("hostname")}/{m5.group("appname")}',
            message=m5.group("msg").strip(),
            format_detected="syslog5424",
        )
    m3 = _SYSLOG3164_RE.match(line)
    if m3:
        return LogEntry(
            raw_line=line,
            timestamp=_parse_timestamp(m3.group("timestamp")),
            level=LogLevel.UNKNOWN,
            source=f'{m3.group("host")}/{m3.group("prog")}',
            message=m3.group("msg").strip(),
            format_detected="syslog3164",
        )
    return None


# --- Application log (Python/Java/Node) ---
_APP_RE = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)'
    r'\s+(?P<level>TRACE|DEBUG|INFO|NOTICE|WARN(?:ING)?|ERROR|CRIT(?:ICAL)?|FATAL|EMERG|ALERT)'
    r'(?:\s+\[?(?P<source>[^\]\s]+)\]?)?'
    r'\s+[-:]?\s*(?P<msg>.*)',
    re.IGNORECASE,
)
_STACKTRACE_INDICATORS = re.compile(
    r'^\s+(?:at |File "|Traceback|Exception|Error:|caused by|\.\.\.)',
    re.IGNORECASE,
)

def _try_app_log(line: str) -> Optional[LogEntry]:
    m = _APP_RE.match(line)
    if not m:
        return None
    return LogEntry(
        raw_line=line,
        timestamp=_parse_timestamp(m.group("timestamp")),
        level=LogLevel.from_str(m.group("level")),
        source=m.group("source"),
        message=m.group("msg").strip(),
        format_detected="app",
    )


# --- Oxlo Warning Report format ---
# Handles structured warning reports like:
#   [WARNING] OXLO WARNING [PRODUCTION]
#   Infra:Backend Logs (500_internal)
#   2x 500 internal errors detected
#   Cause: Internal server error...
#   Sample errors:
#   2026-05-05 22:47:42,646 - app.api.routes.images - ERROR - Img2img failed: ...
_OXLO_REPORT_HEADER = re.compile(
    r'^\[(?:WARNING|ERROR|CRITICAL|INFO)\]\s+OXLO\s+(?:WARNING|ERROR|ALERT)',
    re.IGNORECASE,
)
_OXLO_EMBEDDED_LOG = re.compile(
    r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}[,.\d]*)\s*[-–]\s*'
    r'([a-zA-Z0-9_.]+)\s*[-–]\s*'
    r'(ERROR|WARNING|WARN|CRITICAL|INFO|DEBUG)\s*[-–]\s*(.+)',
)
_OXLO_CAUSE_RE    = re.compile(r'^Cause:\s*(.+)', re.IGNORECASE)
_OXLO_MODULE_RE   = re.compile(r'^Affected modules?:\s*(.+)', re.IGNORECASE)
_OXLO_COUNT_RE    = re.compile(r'^Count:\s*(.+)', re.IGNORECASE)
_OXLO_RCA_RE      = re.compile(r'^Root cause analysis:\s*(.+)', re.IGNORECASE)
_OXLO_INFRA_RE    = re.compile(r'^Infra:(.+)', re.IGNORECASE)

# HTTP status codes inside messages — e.g. "404 Resource Not Found"
_HTTP_STATUS_RE   = re.compile(r"'(\d{3})\s+([^']+)'")
_HTTP_STATUS_LEVEL = {
    "4": LogLevel.ERROR,    # 4xx client errors
    "5": LogLevel.CRITICAL, # 5xx server errors
}


def _is_oxlo_report(text: str) -> bool:
    """Return True if text looks like an Oxlo warning report block."""
    return bool(_OXLO_REPORT_HEADER.search(text[:200]))


def _parse_oxlo_report(text: str) -> List[LogEntry]:
    """
    Pre-process an Oxlo warning report into structured LogEntry objects.

    Extracts:
    - The header severity as a CRITICAL/ERROR/WARNING entry
    - Any embedded app log lines in "Sample errors:" section
    - Cause, affected modules, count as structured entries
    """
    entries: List[LogEntry] = []
    lines = text.splitlines()
    in_sample_errors = False
    header_level = LogLevel.ERROR

    # Determine header severity from the [WARNING]/[ERROR] tag
    first_line = lines[0] if lines else ""
    if "[CRITICAL]" in first_line.upper() or "500" in first_line:
        header_level = LogLevel.CRITICAL
    elif "[WARNING]" in first_line.upper():
        header_level = LogLevel.WARNING

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue

        # Detect "Sample errors:" section
        if re.match(r'^sample errors?:', stripped, re.IGNORECASE):
            in_sample_errors = True
            continue

        # Inside sample errors — try to parse embedded app log lines
        if in_sample_errors:
            m = _OXLO_EMBEDDED_LOG.match(stripped)
            if m:
                ts_raw, source, level_raw, msg = m.groups()
                # Infer level from HTTP status codes in the message
                http_m = _HTTP_STATUS_RE.search(msg)
                if http_m:
                    status_prefix = http_m.group(1)[0]
                    level = _HTTP_STATUS_LEVEL.get(status_prefix, LogLevel.from_str(level_raw))
                else:
                    level = LogLevel.from_str(level_raw)
                entries.append(LogEntry(
                    raw_line=stripped,
                    timestamp=_parse_timestamp(ts_raw),
                    level=level,
                    source=source,
                    message=msg.strip(),
                    format_detected="oxlo_report",
                ))
                continue
            # Truncated / continuation line — attach to last entry if exists
            if entries and stripped and not stripped.startswith("["):
                entries[-1].message += " " + stripped
            continue

        # Structured fields
        m_cause = _OXLO_CAUSE_RE.match(stripped)
        if m_cause:
            entries.append(LogEntry(
                raw_line=stripped, level=header_level,
                message=f"Cause: {m_cause.group(1)}",
                format_detected="oxlo_report",
            ))
            continue

        m_rca = _OXLO_RCA_RE.match(stripped)
        if m_rca:
            entries.append(LogEntry(
                raw_line=stripped, level=header_level,
                message=f"RCA: {m_rca.group(1)}",
                format_detected="oxlo_report",
            ))
            continue

        m_mod = _OXLO_MODULE_RE.match(stripped)
        if m_mod:
            entries.append(LogEntry(
                raw_line=stripped, level=header_level,
                source=m_mod.group(1).strip(),
                message=f"Affected module: {m_mod.group(1).strip()}",
                format_detected="oxlo_report",
            ))
            continue

        m_count = _OXLO_COUNT_RE.match(stripped)
        if m_count:
            entries.append(LogEntry(
                raw_line=stripped, level=header_level,
                message=f"Error count: {m_count.group(1)}",
                format_detected="oxlo_report",
            ))
            continue

        m_infra = _OXLO_INFRA_RE.match(stripped)
        if m_infra:
            entries.append(LogEntry(
                raw_line=stripped, level=header_level,
                message=f"Infrastructure: {m_infra.group(1).strip()}",
                format_detected="oxlo_report",
            ))
            continue

        # Header lines like "[WARNING] OXLO WARNING [PRODUCTION]" or count lines
        if _OXLO_REPORT_HEADER.match(stripped) or re.match(r'^\d+x\s+\d+', stripped):
            entries.append(LogEntry(
                raw_line=stripped, level=header_level,
                message=stripped,
                format_detected="oxlo_report",
            ))

    return entries


# ---------------------------------------------------------------------------
# Parser orchestrator
# ---------------------------------------------------------------------------

_PARSERS = [_try_json, _try_nginx, _try_syslog, _try_app_log]


class LogParser:
    """
    Auto-detects log format and emits ``LogEntry`` objects.

    Multi-line stack traces are stitched onto the preceding entry
    rather than emitted as separate entries.
    """

    def parse(self, text: str) -> List[LogEntry]:
        # ── Oxlo warning report: parse as a block, not line-by-line ──────
        if _is_oxlo_report(text):
            return _parse_oxlo_report(text)

        lines = text.splitlines()
        entries: List[LogEntry] = []
        pending_trace: List[str] = []

        for line in lines:
            if not line.strip():
                continue

            if pending_trace and _STACKTRACE_INDICATORS.match(line):
                pending_trace.append(line)
                continue

            # Flush any accumulated stack trace onto the last entry
            if pending_trace and entries:
                entries[-1].stack_trace = "\n".join(pending_trace)
                pending_trace = []

            entry = self._parse_line(line)
            entries.append(entry)

            # Prime stack-trace accumulation if this looks like an exception
            if entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
                pending_trace = [line]

        # Flush tail
        if pending_trace and entries:
            entries[-1].stack_trace = "\n".join(pending_trace)

        return entries

    def _parse_line(self, line: str) -> LogEntry:
        for parser in _PARSERS:
            entry = parser(line)
            if entry is not None:
                return entry
        return LogEntry(raw_line=line, message=line.strip(), format_detected="plaintext")

    def iter_parse(self, text: str) -> Iterator[LogEntry]:
        yield from self.parse(text)
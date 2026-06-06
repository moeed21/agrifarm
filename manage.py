#!/usr/bin/env python
import os
import sys

# Force UTF-8 on Windows so emoji in logs don't crash the server
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agribazaar.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django not installed. Run: pip install django pandas numpy scikit-learn") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

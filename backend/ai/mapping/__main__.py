"""Entry point of  python -m ai.mapping . It loads backend/.env, then runs the command."""
import sys
from pathlib import Path

from dotenv import load_dotenv

from .cli import main

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
sys.exit(main())

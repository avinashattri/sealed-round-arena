from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_dashboard_renders_without_exceptions():
    app_path = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    at = AppTest.from_file(str(app_path))
    at.run()
    assert not at.exception

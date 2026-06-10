import textwrap

import pytest

from backend.config import load_config, Calendar


def write_config(tmp_path, body):
    path = tmp_path / "config.yaml"
    path.write_text(textwrap.dedent(body))
    return path


def test_load_config_parses_calendars(tmp_path):
    path = write_config(tmp_path, """
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password: "pw1"
            color: "#4A90D9"
          - name: "Work"
            url: "https://baikal.example/dav.php/calendars/user/work/"
            username: "user"
            password: "pw2"
            color: "#F5A623"
    """)
    config = load_config(path)
    assert len(config.calendars) == 2
    first = config.calendars[0]
    assert isinstance(first, Calendar)
    assert first.name == "Personal"
    assert first.color == "#4A90D9"
    assert first.username == "user"
    assert first.password == "pw1"


def test_calendar_id_derived_from_name(tmp_path):
    path = write_config(tmp_path, """
        calendars:
          - name: "Side Projects"
            url: "https://baikal.example/dav.php/calendars/user/sideprojects/"
            username: "user"
            password: "pw"
            color: "#F5A623"
          - name: "Book Club"
            url: "https://baikal.example/dav.php/calendars/user/bookclub/"
            username: "user"
            password: "pw"
            color: "#7ED321"
    """)
    config = load_config(path)
    assert config.calendars[0].id == "sideprojects"
    assert config.calendars[1].id == "bookclub"


def test_explicit_id_overrides_derived(tmp_path):
    path = write_config(tmp_path, """
        calendars:
          - id: "custom"
            name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password: "pw"
            color: "#4A90D9"
    """)
    config = load_config(path)
    assert config.calendars[0].id == "custom"


def test_password_from_env_var_overrides_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CALDAV_CAL_0_PASSWORD", "secret-from-env")
    path = write_config(tmp_path, """
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password: "in-file"
            color: "#4A90D9"
    """)
    config = load_config(path)
    assert config.calendars[0].password == "secret-from-env"


def test_password_env_var_used_when_file_omits_it(tmp_path, monkeypatch):
    monkeypatch.setenv("CALDAV_CAL_0_PASSWORD", "only-in-env")
    path = write_config(tmp_path, """
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            color: "#4A90D9"
    """)
    config = load_config(path)
    assert config.calendars[0].password == "only-in-env"


def test_password_from_file(tmp_path):
    pwfile = tmp_path / "secret"
    pwfile.write_text("file-secret\n")  # trailing newline must be stripped
    path = write_config(tmp_path, f"""
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password_file: "{pwfile}"
            color: "#4A90D9"
    """)
    config = load_config(path)
    assert config.calendars[0].password == "file-secret"


def test_password_file_overrides_inline_password(tmp_path):
    pwfile = tmp_path / "secret"
    pwfile.write_text("from-file")
    path = write_config(tmp_path, f"""
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password: "inline"
            password_file: "{pwfile}"
            color: "#4A90D9"
    """)
    config = load_config(path)
    assert config.calendars[0].password == "from-file"


def test_env_var_overrides_password_file(tmp_path, monkeypatch):
    pwfile = tmp_path / "secret"
    pwfile.write_text("from-file")
    monkeypatch.setenv("CALDAV_CAL_0_PASSWORD", "from-env")
    path = write_config(tmp_path, f"""
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password_file: "{pwfile}"
            color: "#4A90D9"
    """)
    config = load_config(path)
    assert config.calendars[0].password == "from-env"


def test_missing_password_file_raises(tmp_path):
    path = write_config(tmp_path, f"""
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password_file: "{tmp_path / 'nope'}"
            color: "#4A90D9"
    """)
    with pytest.raises(FileNotFoundError):
        load_config(path)


def test_get_calendar_by_id(tmp_path):
    path = write_config(tmp_path, """
        calendars:
          - name: "Personal"
            url: "https://baikal.example/dav.php/calendars/user/personal/"
            username: "user"
            password: "pw"
            color: "#4A90D9"
    """)
    config = load_config(path)
    assert config.get("personal").name == "Personal"
    assert config.get("nope") is None


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does-not-exist.yaml")

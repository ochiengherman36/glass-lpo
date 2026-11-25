from app import cli
from app.extract import ExtractionError
from tests.factories import FakeExtractor, drawing, panel, unclear


def test_cli_writes_outputs_and_prints_a_summary(paper_photo_path, tmp_path, capsys):
    extractor = FakeExtractor(drawing([panel(width_mm=unclear("9?0"))]))

    exit_code = cli.main([str(paper_photo_path), "--out", str(tmp_path / "out")], extractor=extractor)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "LPO LPO-" in output
    assert "Needs human check" in output
    assert "P1: width unclear (raw: '9?0')" in output
    assert (tmp_path / "out" / "result.json").is_file()


def test_cli_reports_errors_and_exits_with_1(paper_photo_path, tmp_path, capsys):
    extractor = FakeExtractor(error=ExtractionError("Could not reach the Anthropic API."))

    exit_code = cli.main([str(paper_photo_path), "--out", str(tmp_path / "out")], extractor=extractor)

    assert exit_code == 1
    assert "Error: Could not reach the Anthropic API." in capsys.readouterr().err


def test_replay_reuses_a_saved_extraction_without_calling_claude(paper_photo_path, tmp_path, capsys):
    first = FakeExtractor(drawing([panel(width_mm=unclear("9?0"))]))
    cli.main([str(paper_photo_path), "--out", str(tmp_path / "first")], extractor=first)
    capsys.readouterr()
    never_called = FakeExtractor(error=AssertionError("Claude must not be called on replay"))

    exit_code = cli.main(
        [str(paper_photo_path), "--out", str(tmp_path / "second"), "--replay", str(tmp_path / "first" / "result.json")],
        extractor=never_called,
    )

    assert exit_code == 0
    assert never_called.calls == []
    assert "P1: width unclear (raw: '9?0')" in capsys.readouterr().out
    assert (tmp_path / "second" / "result.json").is_file()


def test_replay_with_a_missing_file_fails_cleanly(paper_photo_path, tmp_path, capsys):
    exit_code = cli.main([str(paper_photo_path), "--out", str(tmp_path), "--replay", str(tmp_path / "nope.json")])

    assert exit_code == 1
    assert "Error:" in capsys.readouterr().err


def test_cli_reports_unreadable_images(tmp_path, capsys):
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"not an image")

    exit_code = cli.main([str(bad), "--out", str(tmp_path / "out")], extractor=FakeExtractor())

    assert exit_code == 1
    assert "not a readable JPG or PNG" in capsys.readouterr().err

from app.services.evidence_tracker import EvidenceTracker


def test_evidence_tracker_extract_and_verify(sample_resume):
    tracker = EvidenceTracker(sample_resume)
    assert "Worked at Example Corp" in tracker.facts

    updated = sample_resume + "\nLed team"
    missing = tracker.verify(updated)
    assert "Led team" in missing
    assert "Worked at Example Corp" not in missing

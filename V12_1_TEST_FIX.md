# V12.1 test-suite correction

The full Windows test run reported one failure in `test_invalid_recovery_attempt_is_not_shown_as_corrected_code`. The application correctly retained the parser's attempted output for diagnostics, and that output had one inserted closing brace. The test incorrectly required the attempted output to be byte-for-byte identical to the original malformed source.

The test now checks the intended contract: the invalid attempt fails whole-program validation, and `recovered_source` remains exactly the original source. No parser or application behavior was changed by this test-only correction.

# Stockbit Intraday E2E Bridge Preflight Workflow

This workflow is a manual, read-only bridge check on `main`. It verifies the
accepted E2E runtime checkout and reads the canonical E2E input/snapshot bundle
through the existing read-only bridge. It does not call Stockbit/Zapi, write
the Stockbit production prefix, mutate PaperState/counters, or access
outcomes.

The R2 credentials are supplied only to the GitHub Actions process through
repository secrets. No credential is placed in arguments or repository
artifacts. A successful run proves the bridge can read the accepted E2E
bundle; it does not by itself prove a future Stockbit provider capture.

# Synthetic Regression Fixtures

All birth records, locations, relationship labels, questions and outcomes in
the distributable test suite are synthetic or public benchmark material. They
must not be copied from a private chat, profile, gateway session or reading
artifact.

The legacy four-pillar regression uses the deliberately synthetic civil input
`2000-10-18T06:45:00`, location `合成测试地点`, timezone `Asia/Shanghai`.
It exists only to keep deterministic calendar and evidence tests stable. It is
not a production identity or a remembered user profile.

When adding a fixture:

1. generate or select the input independently of private conversations;
2. label it synthetic or cite its public benchmark provenance;
3. omit names, handles, session IDs, message IDs and private artifact paths;
4. keep outcome data separate from blind prediction inputs;
5. extend `scripts/test_repository_privacy.py` when a newly discovered leak
   pattern should be prevented permanently.

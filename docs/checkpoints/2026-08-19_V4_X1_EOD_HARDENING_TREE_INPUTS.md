# V4-X1 EOD hardening merge inputs

Accepted hardening parent: `7b21c50d278b13c8e94cdebddd4ca35765d7274e`

The following hardening blobs are pinned for the controlled integration:

- forward_model_runtime.py `5c56a38f4c6ed013c478e6dbcf889832a47c9ca5`
- forward_monitoring.py `972d86e31f4c163ea64383c63a708da6fb39b0e4`
- providers/idx_index_summary.py `4597b5250f517addcfa09c1964cacd274fe53ced`
- providers/idx_sessions.py `b38b69eb111b183ecc53e1ef7043e462cd4efe55`
- providers/idx_stock_summary.py `2bcb0120a9cd44cd53e77019ade416ca8ea730de`
- security_master.py `6fedc208ec2d3763b7c3945df48da4575d5dad48`
- test_forward_market_context.py `2a56e6d0874ef5f66ef0840d6833fd156405319d`
- test_forward_model_runtime.py `11b5c2878b45aa944e831a8a9d02ae4e8724d7dd`
- test_forward_monitoring.py `4a0902ab6de2245bcb674d72cd56c7de147e0814`
- test_forward_monitoring_runtime.py `f8c701057d9056f3913005eeeea95378ee4af8e0`
- test_idx_sessions_provider.py `d87d060c63dd7494e87391a14349e1d35d607ffb`
- adversarial handoff `e97769125b87a2e7b649562cde04e91fca52e328`
- adversarial checkpoint `9bf1a382f9a04057a59d962ddcc44393cdd077a4`

Resolved conflict blobs prepared for this integration:

- merged forward_eod_runner.py `5d189bc73a901a3abe0a2f94e54a88b71897765d`
- merged test_forward_eod_runner.py `8866a82151d8f2b9804f8c0d64cd4d0146ead210`

The resolved runner retains the 18:00 current-day boundary + morning prior-session catch-up and adds the accepted exact requested-session and no-progress guards.

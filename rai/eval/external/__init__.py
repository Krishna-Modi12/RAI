"""External (third-party) benchmark adapters, kept isolated from the internal RAI benchmark.

`rai.eval` scores the synthetic RAI fleet. Everything under `rai.eval.external` scores RAI
components against a real, independently published dataset instead, using that dataset's own
published scoring protocol rather than an RAI-specific one - so a number produced here can be
compared to the original paper's own reported numbers.
"""

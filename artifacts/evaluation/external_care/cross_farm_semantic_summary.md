# Cross-farm transfer under CARE_SEMANTIC (Gate 5.4 Phase 4)

Fit once on source farm's pooled TRAIN rows using CARE_SEMANTIC-resolved columns, score unmodified on every target-farm dataset, never refit. Feature intersection is computed from the loaded data, not assumed.

| model | source -> target | feature intersection | n datasets (anomaly/normal) | CARE | coverage | earliness | reliability | accuracy | status |
|---|---|---|---|---|---|---|---|---|---|
| isolation_forest | Wind Farm A -> Wind Farm B | wind_speed_ms, wind_direction_deg, power_kw, rotor_rpm, pitch_angle_deg, gearbox_oil_temp_c | 6/9 | 0.574 | 0.716 | 0.468 | 0.682 | 0.503 | COMPUTED |
| zscore_threshold | Wind Farm A -> Wind Farm B | wind_speed_ms, wind_direction_deg, power_kw, rotor_rpm, pitch_angle_deg, gearbox_oil_temp_c | 6/9 | 0.557 | 0.270 | 0.090 | 0.556 | 0.935 | COMPUTED |
| isolation_forest | Wind Farm A -> Wind Farm C | wind_speed_ms, wind_direction_deg, ambient_temp_c, power_kw, rotor_rpm, pitch_angle_deg, nacelle_temp_c, gearbox_oil_temp_c, generator_winding_temp_c | 27/31 | 0.627 | 0.570 | 0.616 | 0.840 | 0.553 | COMPUTED |
| zscore_threshold | Wind Farm A -> Wind Farm C | wind_speed_ms, wind_direction_deg, ambient_temp_c, power_kw, rotor_rpm, pitch_angle_deg, nacelle_temp_c, gearbox_oil_temp_c, generator_winding_temp_c | 27/31 | 0.295 | 0.498 | 0.665 | 0.739 | 0.295 | COMPUTED |
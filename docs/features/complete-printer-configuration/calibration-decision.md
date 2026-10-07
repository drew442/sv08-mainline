# Owner clarification

Probe Z offset is determined by calibration after hardware configuration. Use the starting value illustrated by Sovol factory configuration, and do not copy values that can only be known through calibration. The pinned source comments probe z_offset0 at line71; its SAVE_CONFIG measured1.0 must not become a factory default. Emit a sourced zero starting coordinate reference while calibration remains pending. Generation and stopped application must remain possible before calibration.

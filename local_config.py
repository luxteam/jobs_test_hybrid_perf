tool_name = "hybrid_perf"
report_type = "perf"
show_skipped_groups = True
tracked_metrics = {
    'target_value': {'displaying_name': 'Target value', 'function': 'sum', 'displaying_unit': 'ms'}
}
tracked_metrics_files_number = 10000
analyze_times = {
    'target_value': {'max_diff': 0.05}
}
show_execution_time = True
show_performance_tab = True
show_engine_log = False
tracked_metrics_charts_location = "performance"
show_time_taken = False
show_render_time = False
hide_zero_render_time = True
show_render_log = False
update_baselines_feature_supported = False

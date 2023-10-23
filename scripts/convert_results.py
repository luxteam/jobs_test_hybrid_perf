import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from glob import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from jobs_launcher.core import system_info

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",
                        required=True,
                        type=str,
                        metavar="<path>",
                        help="path to files that should be converted")
    parser.add_argument("--output",
                        required=True,
                        type=str,
                        metavar="<path>",
                        help="path to converted results")

    args = parser.parse_args()

    if os.path.exists(args.output):
        shutil.rmtree(args.output)

    root_dir = os.path.join(args.output, "Results", "HybPerf")
    os.makedirs(root_dir)

    metrics_list = {}
    reports = set(glob(os.path.join(args.input, "*.json")))

    results = {}
    summary = {"duration": 0.0,
               "render_duration": 0.0,
               "execution_time": 0.0,
               "passed": 0,
               "failed": 0,
               "error": 0,
               "skipped": 0,
               "observed": 0,
               "total": 0}

    if reports:
        # save machine_info
        machine_info = system_info.get_machine_info()
        render_device = system_info.get_gpu()
        machine_info["render_device"] = render_device
        machine_info["host"] = system_info.get_host()
        machine_info["tool"] = "HybridPro"
        machine_info["reporting_date"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")

        # go through json reports and save result
        for report in reports:
            render_results = []

            with open(report) as file:
                metrics = json.load(file)
                report_name = os.path.split(report)[1].replace(".json", "")
                report_name = report_name.replace("_main_camera", "").replace("Report_Reduced_", "")
                info = {"duration": 0.0,
                        "render_duration": 0.0,
                        "execution_time": 0.0,
                        "result_path": report_name,
                        "passed": 0,
                        "failed": 0,
                        "error": 0,
                        "skipped": 0,
                        "observed": 0,
                        "total": 0,
                        "render_results": render_results}

                current_report = {"": info}

                for metric in metrics:
                    current_case = {}
                    current_case["message"] = []
                    current_case["number_of_tries"] = 1
                    current_case["test_status"] = "passed"
                    current_case["test_case"] = metric
                    current_case["test_group"] = report_name
                    current_case["tool"] = "HybridPro"
                    current_case["render_device"] = render_device

                    # Presence of 'Cliff detected' field means that metric contains error
                    if "Cliff_detected" in metrics[metric] and metrics[metric]["Cliff_detected"]:
                        current_case["test_status"] = "error"
                        info["error"] += 1
                    # Presence of 'Unexpected acceleration' field means that metric contains warning
                    elif "Unexpected_acceleration" in metrics[metric] and metrics[metric]["Unexpected_acceleration"]:
                        current_case["test_status"] = "failed"
                        info["failed"] += 1
                    else:
                        current_case["test_status"] = "passed"
                        info["passed"] += 1

                    info["total"] += 1

                    description = metrics[metric]["Description"]
                    current_case["frames_to_skip_in_analysis"] = description["frames_to_skip_in_analysis"]
                    current_case["reduction_type"] = description["reduction_type"]
                    current_case["threshold"] = description["threshold"]
                    current_case["deviation_threshold"] = description["deviation_threshold"]

                    current_case["baseline_value"] = metrics[metric]["Reference_value"]
                    current_case["baseline_value_samples_taken"] = metrics[metric]["Reference_value_samples_taken"]
                    current_case["target_value"] = metrics[metric]["Target_value"]
                    current_case["target_value_samples_taken"] = metrics[metric]["Target_value_samples_taken"]
                    current_case["performance_change"] = float(metrics[metric]["Performance_change"].replace("%", ""))
                    current_case["comparison_threshold"] = metrics[metric]["Comparison_threshold"]

                    info["duration"] += metrics[metric]["Target_value"]
                    info["execution_time"] += metrics[metric]["Target_value"]

                    render_results.append(current_case)

                for key in summary:
                    summary[key] += info[key]

                results[report_name] = current_report

            os.makedirs(os.path.join(root_dir, report_name))

            # save results of each test group into separate report_compare.json file
            with open(os.path.join(root_dir, report_name, "report_compare.json"), "w", encoding="utf8") as file:
                json.dump(render_results, file, indent=4, sort_keys=True)

        # save all converted results in session_report.json
        with open(os.path.join(root_dir, "session_report.json"), "w", encoding="utf8") as file:
            json.dump({"machine_info": machine_info, "results": results, "summary": summary},
                      file,
                      indent=4,
                      sort_keys=True)

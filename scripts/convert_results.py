import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from glob import glob

from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from jobs_launcher.core import system_info

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, "jobs_launcher")))
from jobs_launcher.core.reportExporter import process_thumbnail_case

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report",
                        required=True,
                        type=str,
                        metavar="<path>",
                        help="path to files that should be converted")
    parser.add_argument("--telemetry",
                        required=True,
                        type=str,
                        metavar="<path>",
                        help="path to telemetry with rendered images")
    parser.add_argument("--baselines",
                        required=True,
                        type=str,
                        metavar="<path>",
                        help="path to baselines")
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
    reports = set(glob(os.path.join(args.report, "*.json")))

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

                image_name = os.path.split(report)[1].replace("Report_Reduced_", "").replace(".json", ".png")
                rendered_image_path = os.path.join(args.telemetry, image_name)
                if not os.path.exists(rendered_image_path):
                    raise RuntimeError(f"Rendered image {rendered_image_path} can't be found")

                session_dir = os.path.join(root_dir, report_name)
                rendered_color_dir_path = os.path.join(session_dir, "Color")
                os.makedirs(rendered_color_dir_path)
                with Image.open(rendered_image_path) as image:
                    image.save(os.path.join(rendered_color_dir_path,
                               image_name.replace(".png", ".webp")), "webp", quality=75)

                baselines_image_path = os.path.join(args.baselines, image_name)
                if not os.path.exists(baselines_image_path):
                    raise RuntimeError(f"Baseline image {baselines_image_path} can't be found")

                baselines_dir = os.path.join(args.output, "Baseline", report_name)
                baseline_color_dir_path = os.path.join(baselines_dir, "Color")
                os.makedirs(baseline_color_dir_path)
                with Image.open(baselines_image_path) as image:
                    image.save(os.path.join(baseline_color_dir_path,
                               image_name.replace(".png", ".webp")), "webp", quality=75)

                image_name = image_name.replace(".png", ".webp")

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

                    current_case["render_color_path"] = os.path.join("Color", image_name)
                    current_case["baseline_color_path"] = os.path.join("..",
                                                                       "..",
                                                                       "..",
                                                                       "Baseline",
                                                                       report_name,
                                                                       "Color",
                                                                       image_name)

                    info["duration"] += metrics[metric]["Target_value"]
                    info["execution_time"] += metrics[metric]["Target_value"]

                    render_results.append(current_case)

                # generate thumbnails only once
                process_thumbnail_case(session_dir, current_case, 128, "render_color_path")
                process_thumbnail_case(session_dir, current_case, 256, "render_color_path")
                process_thumbnail_case(session_dir, current_case, 128, "baseline_color_path")
                process_thumbnail_case(session_dir, current_case, 256, "baseline_color_path")

                # add path to thumbnails to all test cases
                for metric in render_results:
                    metric["thumb128_render_color_path"] = current_case["thumb128_render_color_path"]
                    metric["thumb256_render_color_path"] = current_case["thumb256_render_color_path"]
                    metric["thumb128_baseline_color_path"] = current_case["thumb128_baseline_color_path"]
                    metric["thumb256_baseline_color_path"] = current_case["thumb256_baseline_color_path"]

                for key in summary:
                    summary[key] += info[key]

                results[report_name] = current_report

            # save results of each test group into separate report_compare.json file
            with open(os.path.join(root_dir, report_name, "report_compare.json"), "w", encoding="utf8") as file:
                json.dump(render_results, file, indent=4, sort_keys=True)

            # update paths to images
            for metric in render_results:
                metric["render_color_path"] = os.path.join(report_name, current_case["render_color_path"])
                metric["thumb128_render_color_path"] = os.path.join(report_name,
                                                                    current_case["thumb128_render_color_path"])
                metric["thumb256_render_color_path"] = os.path.join(report_name,
                                                                    current_case["thumb256_render_color_path"])

                metric["baseline_color_path"] = os.path.join("..",
                                                             "..",
                                                             "Baseline",
                                                             report_name,
                                                             "Color",
                                                             image_name)
                metric["thumb128_baseline_color_path"] = os.path.join("..",
                                                                      "..",
                                                                      "Baseline",
                                                                      report_name,
                                                                      "Color",
                                                                      os.path.split(current_case["thumb128_baseline_color_path"])[1])  # noqa: E501
                metric["thumb256_baseline_color_path"] = os.path.join("..",
                                                                      "..",
                                                                      "Baseline",
                                                                      report_name,
                                                                      "Color",
                                                                      os.path.split(current_case["thumb128_baseline_color_path"])[1])  # noqa: E501

        # save all converted results in session_report.json
        with open(os.path.join(root_dir, "session_report.json"), "w", encoding="utf8") as file:
            json.dump({"machine_info": machine_info, "results": results, "summary": summary},
                      file,
                      indent=4,
                      sort_keys=True)

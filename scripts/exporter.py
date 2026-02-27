import os
import json
import csv
import html
from datetime import datetime
from typing import List, Dict
from urllib.parse import urlparse

from scripts.logger import get_logger

adv_logger = get_logger('logs')

class ResultExporter:
    
    def __init__(self, config):
        self.config = config
        self.results_dir = config.RESULTS_DIR
        self.supported_formats = ["json", "html", "csv", "txt"]
        if not hasattr(config, 'EXPORT_FORMATS') or not config.EXPORT_FORMATS:
            self.config.EXPORT_FORMATS = ["json", "html"]
            adv_logger.log_info("No export formats configured, using defaults: json, html")
            
        os.makedirs(self.results_dir, exist_ok=True)
        adv_logger.log_info(f"Ensuring results directory exists: {self.results_dir}")
    
    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _get_result_filename(self, base_filename: str = "", format_type: str = "json") -> str:
        timestamp = self._get_timestamp()
        if base_filename:
            safe_basename = os.path.basename(base_filename)
            return f"{self.results_dir}/{safe_basename}_{timestamp}.{format_type}"
        else:
            return f"{self.results_dir}/results_{timestamp}.{format_type}"
    
    def _ensure_result_has_required_fields(self, result: Dict) -> Dict:
        required_fields = {
            "url": "Unknown",
            "status_code": 0,
            "title": "Unknown",
            "confidence": 0.0,
            "found": False,
            "has_login_form": False,
            "technologies": [],
            "headers": {},
            "server": "Unknown",
            "forms": [],
            "inputs": [],
            "content_length": 0
        }
        
        safe_result = result.copy()
        
        if "headers" in safe_result and "Server" in safe_result["headers"]:
            safe_result["server"] = safe_result["headers"]["Server"]
        
        for field, default_value in required_fields.items():
            if field not in safe_result or safe_result[field] is None:
                safe_result[field] = default_value
                
        return safe_result
    
    def _export_json(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        try:
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]
            
            export_data = {
                "scan_info": scan_info,
                "results": safe_results,
                "total_count": len(safe_results),
                "found_count": sum(1 for r in safe_results if r.get("found", False)),
                "export_time": datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            adv_logger.log_info(f"Exported {len(results)} results to JSON: {filename}")
            return True
        except Exception as e:
            adv_logger.log_error(f"Failed to export to JSON: {str(e)}")
            return False
    
    def _export_html(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        try:
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]

            url = html.escape(scan_info.get("target_url", "Unknown"))
            mode = html.escape(scan_info.get("scan_mode", "Unknown"))
            duration = scan_info.get("scan_time", 0)
            total_paths = scan_info.get("total_paths", 0)
            found_count = sum(1 for r in safe_results if r.get("found", False))

            html_content = (
                "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
                "<title>Admin Panel Finder Report</title>"
                "<style>"
                "body{font-family:sans-serif;margin:2em;background:#1a1a2e;color:#e0e0e0}"
                "h1{color:#00d2ff}table{border-collapse:collapse;width:100%}"
                "th,td{border:1px solid #333;padding:8px;text-align:left}"
                "th{background:#16213e}.success{color:#0f0}.warning{color:#fa0}.error{color:#f33}"
                ".badge{padding:2px 8px;border-radius:4px;font-size:0.85em;margin:0 2px}"
                ".badge-green{background:#0a3;color:#fff}.badge-blue{background:#07c;color:#fff}"
                ".badge-orange{background:#c60;color:#fff}"
                "a{color:#00d2ff}"
                "</style></head><body>"
                f"<h1>Scan Report — {url}</h1>"
                f"<p>Mode: <b>{mode}</b> | Paths checked: <b>{total_paths}</b> | "
                f"Found: <b>{found_count}</b> | Duration: <b>{duration:.2f}s</b></p>"
            )

            if not safe_results:
                html_content += "<p>No potential admin panels found.</p>"
            else:
                html_content += (
                    "<table><tr><th>#</th><th>URL</th><th>Status</th><th>Title</th>"
                    "<th>Confidence</th><th>Features</th><th>Technologies</th></tr>"
                )

                for idx, result in enumerate(safe_results, 1):
                    confidence = result.get("confidence", 0) * 100
                    confidence_class = "success" if confidence > 70 else "warning" if confidence > 40 else "error"

                    features_parts = []
                    if result.get("has_login_form", False):
                        features_parts.append('<span class="badge badge-green">Login Form</span>')
                    if result.get("forms") and len(result["forms"]) > 0:
                        features_parts.append(f'<span class="badge badge-blue">{len(result["forms"])} Forms</span>')
                    if result.get("status_code", 0) in (401, 403):
                        features_parts.append('<span class="badge badge-orange">Auth Required</span>')
                    features_html = " ".join(features_parts)

                    techs_html = ""
                    if result.get("technologies"):
                        techs_html = ", ".join(html.escape(t) for t in result["technologies"])

                    result_url = html.escape(result.get("url", "Unknown"))
                    result_title = html.escape(result.get("title", "Unknown"))

                    html_content += (
                        f"<tr><td>{idx}</td>"
                        f'<td><a href="{result_url}" target="_blank">{result_url}</a></td>'
                        f"<td>{result.get('status_code', 0)}</td>"
                        f"<td>{result_title}</td>"
                        f'<td class="{confidence_class}">{confidence:.1f}%</td>'
                        f"<td>{features_html}</td>"
                        f"<td>{techs_html}</td></tr>"
                    )

                html_content += "</table>"

            html_content += "</body></html>"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            adv_logger.log_info(f"Exported {len(results)} results to HTML: {filename}")
            return True

        except Exception as e:
            adv_logger.log_error(f"Failed to export to HTML: {str(e)}")
            return False
    
    def _export_csv(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        try:
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                writer.writerow([
                    "URL", "Status", "Title", "Confidence", "Has Login Form", 
                    "Technologies", "Server", "Content Length", "Form Count"
                ])
                
                for result in safe_results:
                    writer.writerow([
                        result.get("url", "Unknown"),
                        result.get("status_code", "Unknown"),
                        result.get("title", "Unknown"),
                        f"{result.get('confidence', 0) * 100:.1f}%",
                        "Yes" if result.get("has_login_form", False) else "No",
                        ", ".join(result.get("technologies", [])),
                        result.get("server", "Unknown"),
                        result.get("content_length", 0),
                        len(result.get("forms", []))
                    ])
            
            adv_logger.log_info(f"Exported {len(results)} results to CSV: {filename}")
            return True
            
        except Exception as e:
            adv_logger.log_error(f"Failed to export to CSV: {str(e)}")
            return False
    
    def _export_txt(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        try:
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("===== Admin Panel Finder Results =====\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"Target URL: {scan_info.get('target_url', 'Unknown')}\n")
                f.write(f"Scan Mode: {scan_info.get('scan_mode', 'Unknown')}\n")
                f.write(f"Total Paths Checked: {scan_info.get('total_paths', 0)}\n")
                f.write(f"Scan Duration: {scan_info.get('scan_time', 0):.2f} seconds\n\n")
                
                f.write(f"Found {len(safe_results)} potential admin panels\n\n")
                
                for i, result in enumerate(safe_results, 1):
                    confidence = result.get("confidence", 0) * 100
                    f.write(f"[{i}] {result.get('url', 'Unknown')}\n")
                    f.write(f"    Status Code: {result.get('status_code', 'Unknown')}\n")
                    f.write(f"    Title: {result.get('title', 'Unknown')}\n")
                    f.write(f"    Confidence: {confidence:.1f}%\n")
                    f.write(f"    Server: {result.get('server', 'Unknown')}\n")
                    
                    f.write(f"    Has Login Form: {'Yes' if result.get('has_login_form', False) else 'No'}\n")
                    
                    if result.get("technologies", []):
                        f.write(f"    Technologies: {', '.join(result.get('technologies', []))}\n")
                    
                    f.write("\n")
            
            adv_logger.log_info(f"Exported {len(results)} results to TXT: {filename}")
            return True
            
        except Exception as e:
            adv_logger.log_error(f"Failed to export to TXT: {str(e)}")
            return False
    
    def export_results(self, results: List[Dict], scan_info: Dict, format_type: str = "", base_filename: str = "") -> Dict[str, bool]:
        if not results or not isinstance(results, list):
            adv_logger.log_warning("No results to export")
            return {}
            
        os.makedirs(self.results_dir, exist_ok=True)
        
        found_results = [r for r in results if isinstance(r, dict) and r.get("found", False)]
        
        if not found_results:
            adv_logger.log_info("No positive results to export")
            
        if not format_type:
            format_type = self.config.EXPORT_FORMATS[0] if self.config.EXPORT_FORMATS else "json"
            
        formats_to_export = []
        if format_type.lower() == "all":
            formats_to_export = self.supported_formats
        else:
            formats_to_export = [format_type.lower()]
            
        export_status = {}
        
        base_target_url = scan_info.get("target_url", "")
        if base_target_url:
            parsed = urlparse(base_target_url)
            base_domain = parsed.netloc
            timestamp = self._get_timestamp()
            base_filename = f"{base_domain}_{timestamp}" if base_domain else f"scan_{timestamp}"
        
        for fmt in formats_to_export:
            if fmt not in self.supported_formats:
                adv_logger.log_warning(f"Unsupported export format: {fmt}")
                export_status[fmt] = False
                continue
                
            filename = self._get_result_filename(base_filename, fmt)
            
            if fmt == "json":
                export_status[fmt] = self._export_json(results, scan_info, filename)
            elif fmt == "html":
                export_status[fmt] = self._export_html(results, scan_info, filename)
            elif fmt == "csv":
                export_status[fmt] = self._export_csv(results, scan_info, filename)
            elif fmt == "txt":
                export_status[fmt] = self._export_txt(results, scan_info, filename)
            else:
                adv_logger.log_warning(f"Format {fmt} recognized but no export function available")
                export_status[fmt] = False
                
        successful_formats = [f for f, status in export_status.items() if status]
        adv_logger.log_results_exported(successful_formats, len(found_results))
        
        return export_status
    
    def list_result_files(self) -> List[str]:
        try:
            if not os.path.exists(self.results_dir):
                return []
                
            result_files = []
            for filename in os.listdir(self.results_dir):
                if filename.endswith((".json", ".html", ".csv", ".txt")):
                    result_files.append(filename)
                    
            return sorted(result_files, reverse=True)
            
        except Exception as e:
            adv_logger.log_error(f"Failed to list result files: {str(e)}")
            return []
    
    def view_result_file(self, filename: str) -> str:

        try:
            filepath = os.path.join(self.results_dir, filename)
            
            if not os.path.exists(filepath):
                return ""
                
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            adv_logger.log_error(f"Failed to view result file: {str(e)}")
            return ""

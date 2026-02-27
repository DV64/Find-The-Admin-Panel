import os
import json
import shutil
import requests

from scripts.logger import get_logger

adv_logger = get_logger('logs')


def auto_update_wordlist(wordlist_path, update_source=None):
    try:
        adv_logger.log_info(f"Attempting to auto-update wordlist: {wordlist_path}")

        if not os.path.exists(wordlist_path):
            parent_dir = os.path.dirname(wordlist_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            with open(wordlist_path, 'w') as f:
                json.dump([], f)
            adv_logger.log_info(f"Created new empty wordlist at {wordlist_path}")

        with open(wordlist_path, 'r') as f:
            try:
                existing_paths = json.load(f)
                if not isinstance(existing_paths, list):
                    existing_paths = []
                    adv_logger.log_warning(f"Wordlist {wordlist_path} has invalid format, resetting to empty list")
            except json.JSONDecodeError:
                existing_paths = []
                adv_logger.log_warning(f"Wordlist {wordlist_path} has invalid JSON, resetting to empty list")

        original_count = len(existing_paths)
        adv_logger.log_info(f"Current wordlist has {original_count} entries")

        new_paths = []
        if update_source and update_source.startswith(('http://', 'https://')):
            try:
                headers = {
                    'User-Agent': 'FindTheAdminPanel/7.0 WordlistUpdater'
                }
                response = requests.get(update_source, timeout=10, headers=headers, verify=False)

                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')

                    if 'json' in content_type:
                        fetched_data = response.json()
                        if isinstance(fetched_data, list):
                            new_paths = fetched_data
                        elif isinstance(fetched_data, dict) and 'paths' in fetched_data:
                            new_paths = fetched_data.get('paths', [])
                    else:
                        new_paths = [line.strip() for line in response.text.split('\n') if line.strip()]

                    adv_logger.log_info(f"Fetched {len(new_paths)} paths from {update_source}")
                else:
                    adv_logger.log_warning(f"Failed to fetch paths from {update_source}, status code: {response.status_code}")
            except Exception as e:
                adv_logger.log_error(f"Error fetching paths from {update_source}: {str(e)}")

        elif update_source and os.path.isfile(update_source):
            try:
                with open(update_source, 'r') as f:
                    if update_source.endswith('.json'):
                        try:
                            fetched_data = json.load(f)
                            if isinstance(fetched_data, list):
                                new_paths = fetched_data
                            elif isinstance(fetched_data, dict) and 'paths' in fetched_data:
                                new_paths = fetched_data.get('paths', [])
                        except json.JSONDecodeError:
                            f.seek(0)
                            new_paths = [line.strip() for line in f if line.strip()]
                    else:
                        new_paths = [line.strip() for line in f if line.strip()]

                adv_logger.log_info(f"Read {len(new_paths)} paths from file {update_source}")
            except Exception as e:
                adv_logger.log_error(f"Error reading paths from file {update_source}: {str(e)}")

        else:
            admin_patterns = [
                "admin", "administrator", "admincp", "admins", "admin/login", "admin/dashboard",
                "login", "wp-admin", "wp-login.php", "panel", "cpanel", "control", "dashboard",
                "adm", "moderator", "webadmin", "adminarea", "bb-admin", "adminLogin", "admin_area",
                "backend", "cmsadmin", "administration", "cms", "manage", "portal", "supervisor",
                "manager", "mgr", "user/admin", "user/login", "siteadmin", "console", "admin1",
                "adminpanel", "robots.txt", "sitemap.xml", ".env", ".git/config", ".htaccess",
                "server-status", "phpmyadmin", "myadmin", "pma", "system", "admincontrol"
            ]

            variants = []
            for pattern in admin_patterns:
                variants.append(pattern)
                variants.append(f"{pattern}/")
                variants.append(f"{pattern}.php")
                variants.append(f"{pattern}.html")
                variants.append(f"{pattern}.asp")
                variants.append(f"{pattern}.aspx")
                variants.append(f"{pattern}.jsp")

            new_paths = list(set(variants))
            adv_logger.log_info(f"Generated {len(new_paths)} admin path patterns for enrichment")

        combined_paths = list(set(existing_paths + new_paths))

        combined_paths.sort()

        backup_path = f"{wordlist_path}.bak"
        try:
            shutil.copy2(wordlist_path, backup_path)
            adv_logger.log_info(f"Created backup at {backup_path}")
        except Exception as e:
            adv_logger.log_warning(f"Failed to create backup: {str(e)}")

        with open(wordlist_path, 'w') as f:
            json.dump(combined_paths, f, indent=2)

        final_count = len(combined_paths)
        added_count = final_count - original_count
        stats = {
            "original_count": original_count,
            "final_count": final_count,
            "added_count": added_count,
            "percent_increase": round((added_count / max(original_count, 1)) * 100, 2)
        }

        message = f"Wordlist updated successfully. Added {added_count} new paths ({stats['percent_increase']}% increase)"
        adv_logger.log_info(message)

        return True, message, stats

    except Exception as e:
        error_msg = f"Error updating wordlist: {str(e)}"
        adv_logger.log_error(error_msg)
        return False, error_msg, {}


from typing import List, Set, Generator, Dict
from scripts.constants import (
    FUZZING_EXTENSIONS, BACKUP_EXTENSIONS,
    PRIORITY_PATH_KEYWORDS, ADMIN_KEYWORDS
)


class PathFuzzer:
    
    def __init__(
        self,
        depth: int = 1,
        include_extensions: bool = True,
        include_backups: bool = True,
        include_case_variations: bool = True,
        include_separator_variations: bool = True,
        max_variations_per_path: int = 50
    ):
        self.depth = max(1, min(depth, 3))
        self.include_extensions = include_extensions
        self.include_backups = include_backups
        self.include_case_variations = include_case_variations
        self.include_separator_variations = include_separator_variations
        self.max_variations_per_path = max_variations_per_path
        
        if self.depth == 1:
            self.extensions = ['.php', '.html', '.asp']
        elif self.depth == 2:
            self.extensions = ['.php', '.html', '.asp', '.aspx', '.jsp', '.htm']
        else:
            self.extensions = FUZZING_EXTENSIONS
        
        if self.depth == 1:
            self.backup_extensions = ['.bak', '.old']
        elif self.depth == 2:
            self.backup_extensions = ['.bak', '.old', '.backup', '.orig']
        else:
            self.backup_extensions = BACKUP_EXTENSIONS
    
    def fuzz_path(self, path: str) -> List[str]:
        variations: Set[str] = set()
        variations.add(path)
        
        path = path.strip('/')
        
        parts = path.split('/')
        basename = parts[-1] if parts else path
        
        if '.' in basename:
            name, ext = basename.rsplit('.', 1)
            original_ext = '.' + ext
        else:
            name = basename
            original_ext = ''
        
        if self.include_extensions:
            for ext in self.extensions:
                new_basename = name + ext
                if len(parts) > 1:
                    new_path = '/'.join(parts[:-1]) + '/' + new_basename
                else:
                    new_path = new_basename
                variations.add(new_path)
                
                if len(parts) > 1:
                    variations.add('/'.join(parts[:-1]) + '/' + name)
                else:
                    variations.add(name)
        
        if self.include_backups:
            for backup_ext in self.backup_extensions:
                variations.add(path + backup_ext)
                
                if original_ext:
                    base_path = path[:-len(original_ext)]
                    variations.add(base_path + backup_ext)
                    
                    variations.add(base_path + backup_ext + original_ext)
        
        if self.include_case_variations:
            variations.add(path.lower())
            variations.add(path.upper())
            
            variations.add(self._to_camel_case(path))
            variations.add(self._to_title_case(path))
        
        if self.include_separator_variations:
            variations.add(path.replace('_', '-'))
            variations.add(path.replace('-', '_'))
            
            variations.add(path.replace('_', '').replace('-', ''))
        
        result = list(variations)[:self.max_variations_per_path]
        
        return result
    
    def fuzz_paths(self, paths: List[str]) -> List[str]:
        all_variations: Set[str] = set()
        
        for path in paths:
            variations = self.fuzz_path(path)
            all_variations.update(variations)
        
        return list(all_variations)
    
    def generate_admin_paths(self) -> List[str]:
        paths: Set[str] = set()
        
        base_paths = [
            'admin', 'administrator', 'admincp', 'admin_area', 'admin_panel',
            'dashboard', 'control', 'controlpanel', 'cp', 'cpanel',
            'backend', 'backoffice', 'manage', 'manager', 'management',
            'login', 'signin', 'auth', 'authentication',
            'panel', 'webadmin', 'sysadmin', 'adm', 'admin1', 'admin2',
            'moderator', 'webmaster', 'site_admin', 'staff'
        ]
        
        cms_paths = [
            'wp-admin', 'wp-login.php', 'wp-admin/admin.php',
            'administrator/index.php', 'joomla/administrator',
            'user/login', 'admin/login', 'admin/dashboard',
            'adminpanel', 'admins', 'admin_login', 'user/admin'
        ]
        
        paths.update(base_paths)
        paths.update(cms_paths)
        
        if self.depth >= 2:
            extended_paths: Set[str] = set()
            
            for path in base_paths:
                extended_paths.add(f"{path}/login")
                extended_paths.add(f"{path}/index")
                extended_paths.add(f"{path}/dashboard")
                extended_paths.add(f"{path}/home")
                
                for ext in self.extensions[:3]:
                    extended_paths.add(f"{path}{ext}")
                    extended_paths.add(f"{path}/login{ext}")
                    extended_paths.add(f"{path}/index{ext}")
            
            paths.update(extended_paths)
        
        return list(paths)
    
    def generate_api_paths(self) -> List[str]:
        paths = [
            'api', 'api/v1', 'api/v2', 'api/admin', 'api/users',
            'rest', 'rest/api', 'graphql', 'graphiql',
            'swagger', 'swagger-ui', 'api-docs', 'docs/api',
            'openapi', 'openapi.json', 'openapi.yaml',
            'wsdl', 'soap', 'xmlrpc', 'jsonrpc',
            '.well-known', 'health', 'status', 'ping',
            'ws', 'websocket', 'socket.io'
        ]
        
        return paths
    
    def prioritize_paths(self, paths: List[str]) -> List[str]:
        def score_path(path: str) -> int:
            score = 0
            path_lower = path.lower()
            
            for keyword in PRIORITY_PATH_KEYWORDS:
                if keyword in path_lower:
                    score += 10
            
            basename = path.split('/')[-1].split('.')[0]
            if basename.lower() in ['admin', 'administrator', 'dashboard', 'login']:
                score += 20
            
            if len(path) > 50:
                score -= 5
            
            if path.endswith('.php') or path.endswith('.aspx'):
                score += 3
            
            return score
        
        return sorted(paths, key=score_path, reverse=True)
    
    def _to_camel_case(self, s: str) -> str:
        parts = s.replace('-', '_').split('_')
        return ''.join(word.capitalize() for word in parts)
    
    def _to_title_case(self, s: str) -> str:
        parts = s.replace('-', '_').split('_')
        return '_'.join(word.capitalize() for word in parts)


class WordlistMutator:
    
    def __init__(self, max_mutations: int = 10):
        self.max_mutations = max_mutations
    
    def mutate(self, word: str) -> List[str]:
        mutations: Set[str] = set()
        mutations.add(word)
        
        substitutions = {
            'a': ['@', '4'],
            'e': ['3'],
            'i': ['1', '!'],
            'o': ['0'],
            's': ['$', '5'],
            't': ['7']
        }
        
        for char, replacements in substitutions.items():
            if char in word.lower():
                for replacement in replacements:
                    mutations.add(word.lower().replace(char, replacement))
        
        for i in range(1, 4):
            mutations.add(word + str(i))
        
        for year in ['2024', '2025', '123', '1234']:
            mutations.add(word + year)
        
        for prefix in ['_', '-', '.', '']:
            mutations.add(prefix + word)
        
        return list(mutations)[:self.max_mutations]
    
    def mutate_wordlist(self, words: List[str]) -> List[str]:
        all_mutations: Set[str] = set()
        
        for word in words:
            mutations = self.mutate(word)
            all_mutations.update(mutations)
        
        return list(all_mutations)


_fuzzer: PathFuzzer = None


def get_fuzzer(depth: int = 1) -> PathFuzzer:
    global _fuzzer
    if _fuzzer is None or _fuzzer.depth != depth:
        _fuzzer = PathFuzzer(depth=depth)
    return _fuzzer


def fuzz_paths(paths: List[str], depth: int = 1) -> List[str]:
    fuzzer = get_fuzzer(depth)
    return fuzzer.fuzz_paths(paths)


def generate_admin_paths(depth: int = 1) -> List[str]:
    fuzzer = get_fuzzer(depth)
    return fuzzer.generate_admin_paths()

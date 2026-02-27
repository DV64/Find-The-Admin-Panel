
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from scripts.constants import ADMIN_KEYWORDS


@dataclass
class EndpointInfo:
    url: str
    endpoint_type: str
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)
    introspection_result: Optional[Dict] = None


class WebSocketDetector:
    
    def __init__(self):
        self.ws_patterns = [
            r'ws://[^\s"\'<>]+',
            r'wss://[^\s"\'<>]+',
            r'new\s+WebSocket\s*\(["\']([^"\']+)["\']\)',
            r'socket\.io',
            r'sockjs',
            r'Upgrade:\s*websocket',
        ]
        
        self.ws_paths = [
            '/ws', '/websocket', '/socket', '/socket.io',
            '/sockjs', '/realtime', '/live', '/stream',
            '/ws/admin', '/admin/ws', '/api/ws'
        ]
    
    def detect(self, content: str, headers: Dict[str, str], url: str) -> List[EndpointInfo]:
        endpoints = []
        
        if 'Upgrade' in headers and 'websocket' in headers.get('Upgrade', '').lower():
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='websocket',
                confidence=0.9,
                details={'source': 'header', 'type': 'upgrade'}
            ))
        
        for pattern in self.ws_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ''
                
                if match and ('ws://' in match or 'wss://' in match):
                    endpoints.append(EndpointInfo(
                        url=match,
                        endpoint_type='websocket',
                        confidence=0.85,
                        details={'source': 'content', 'pattern': pattern}
                    ))
        
        return endpoints
    
    def get_common_paths(self) -> List[str]:
        return self.ws_paths


class GraphQLDetector:
    
    def __init__(self):
        self.graphql_paths = [
            '/graphql', '/graphiql', '/api/graphql', '/v1/graphql',
            '/query', '/gql', '/playground', '/explorer',
            '/admin/graphql', '/graphql/admin'
        ]
        
        self.graphql_indicators = [
            'graphql', 'GraphQL', '__schema', '__type',
            'query {', 'mutation {', 'subscription {',
            'graphiql', 'playground', 'apollo'
        ]
        
        self.introspection_query = '''
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                types {
                    name
                    kind
                    description
                }
            }
        }
        '''
    
    def detect(self, content: str, headers: Dict[str, str], url: str) -> List[EndpointInfo]:
        endpoints = []
        
        content_type = headers.get('Content-Type', '')
        if 'application/graphql' in content_type:
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='graphql',
                confidence=0.95,
                details={'source': 'content_type'}
            ))
        
        indicator_count = sum(1 for ind in self.graphql_indicators if ind in content)
        if indicator_count >= 2:
            confidence = min(0.9, 0.5 + indicator_count * 0.1)
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='graphql',
                confidence=confidence,
                details={'source': 'content', 'indicator_count': indicator_count}
            ))
        
        if '__schema' in content or '__type' in content:
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='graphql',
                confidence=0.95,
                details={'source': 'schema_detected'}
            ))
        
        return endpoints
    
    def get_introspection_query(self) -> str:
        return self.introspection_query
    
    def get_common_paths(self) -> List[str]:
        return self.graphql_paths


class RESTAPIDetector:
    
    def __init__(self):
        self.api_paths = [
            '/api', '/api/v1', '/api/v2', '/api/v3',
            '/rest', '/rest/api', '/v1', '/v2',
            '/api/admin', '/admin/api', '/api/users',
            '/api-docs', '/docs/api', '/swagger',
            '/swagger-ui', '/swagger.json', '/swagger.yaml',
            '/openapi', '/openapi.json', '/openapi.yaml',
            '/redoc', '/api/docs'
        ]
        
        self.api_indicators = [
            'swagger', 'openapi', 'api-docs', 'REST',
            'application/json', 'endpoints', 'routes',
            '"paths":', '"info":', '"swagger":', '"openapi":',
            'x-api-key', 'Authorization'
        ]
    
    def detect(self, content: str, headers: Dict[str, str], url: str) -> List[EndpointInfo]:
        endpoints = []
        
        is_swagger = '"swagger"' in content or '"openapi"' in content
        if is_swagger:
            try:
                api_spec = json.loads(content)
                if 'swagger' in api_spec or 'openapi' in api_spec:
                    endpoints.append(EndpointInfo(
                        url=url,
                        endpoint_type='rest_api',
                        confidence=0.95,
                        details={
                            'source': 'swagger_spec',
                            'version': api_spec.get('swagger') or api_spec.get('openapi'),
                            'title': api_spec.get('info', {}).get('title', 'Unknown API')
                        }
                    ))
            except json.JSONDecodeError:
                pass
        
        indicator_count = sum(1 for ind in self.api_indicators if ind.lower() in content.lower())
        if indicator_count >= 2:
            confidence = min(0.85, 0.4 + indicator_count * 0.1)
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='rest_api',
                confidence=confidence,
                details={'source': 'content', 'indicator_count': indicator_count}
            ))
        
        if 'x-api-key' in str(headers).lower() or 'x-ratelimit' in str(headers).lower():
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='rest_api',
                confidence=0.7,
                details={'source': 'headers'}
            ))
        
        return endpoints
    
    def get_common_paths(self) -> List[str]:
        return self.api_paths


class SOAPDetector:
    
    def __init__(self):
        self.soap_paths = [
            '/soap', '/wsdl', '/service.wsdl', '/services',
            '/ws', '/webservice', '/webservices',
            '/asmx', '/axis', '/axis2', '/cxf',
            '?wsdl', '?WSDL'
        ]
        
        self.soap_indicators = [
            'wsdl:', 'soap:', 'xmlns:soap', 'xmlns:wsdl',
            'soap:Envelope', 'wsdl:definitions', 'targetNamespace',
            'soap:Body', 'portType', 'binding', 'service'
        ]
    
    def detect(self, content: str, headers: Dict[str, str], url: str) -> List[EndpointInfo]:
        endpoints = []
        
        content_type = headers.get('Content-Type', '')
        if 'text/xml' in content_type or 'application/soap+xml' in content_type:
            if any(ind in content for ind in self.soap_indicators):
                endpoints.append(EndpointInfo(
                    url=url,
                    endpoint_type='soap',
                    confidence=0.9,
                    details={'source': 'content_type_and_content'}
                ))
        
        if 'wsdl:definitions' in content or '<definitions' in content:
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='soap',
                confidence=0.95,
                details={'source': 'wsdl_detected', 'is_wsdl': True}
            ))
        
        if 'soap:Envelope' in content or 'SOAP-ENV:Envelope' in content:
            endpoints.append(EndpointInfo(
                url=url,
                endpoint_type='soap',
                confidence=0.9,
                details={'source': 'soap_envelope'}
            ))
        
        return endpoints
    
    def get_common_paths(self) -> List[str]:
        return self.soap_paths


class AdvancedDetector:
    
    def __init__(self):
        self.websocket = WebSocketDetector()
        self.graphql = GraphQLDetector()
        self.rest_api = RESTAPIDetector()
        self.soap = SOAPDetector()
    
    def detect_all(
        self,
        content: str,
        headers: Dict[str, str],
        url: str
    ) -> Dict[str, List[EndpointInfo]]:
        return {
            'websocket': self.websocket.detect(content, headers, url),
            'graphql': self.graphql.detect(content, headers, url),
            'rest_api': self.rest_api.detect(content, headers, url),
            'soap': self.soap.detect(content, headers, url)
        }
    
    def get_all_paths(self) -> List[str]:
        paths = []
        paths.extend(self.websocket.get_common_paths())
        paths.extend(self.graphql.get_common_paths())
        paths.extend(self.rest_api.get_common_paths())
        paths.extend(self.soap.get_common_paths())
        return list(set(paths))
    
    def analyze_admin_potential(
        self,
        content: str,
        title: str,
        url: str,
        headers: Dict[str, str]
    ) -> Tuple[float, Dict[str, Any]]:
        confidence_boost = 0.0
        details = {
            'endpoints_found': [],
            'admin_indicators': [],
            'security_features': []
        }
        
        all_endpoints = self.detect_all(content, headers, url)
        
        for endpoint_type, endpoints in all_endpoints.items():
            if endpoints:
                details['endpoints_found'].append({
                    'type': endpoint_type,
                    'count': len(endpoints)
                })
                if any('admin' in e.url.lower() for e in endpoints):
                    confidence_boost += 0.1
        
        admin_patterns = [
            (r'role\s*[=:]\s*["\']?admin', 0.15),
            (r'permission\s*[=:]\s*["\']?admin', 0.15),
            (r'isAdmin\s*[=:]\s*true', 0.2),
            (r'user_type\s*[=:]\s*["\']?admin', 0.15),
            (r'admin_access', 0.1),
        ]
        
        for pattern, boost in admin_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                confidence_boost += boost
                details['admin_indicators'].append(pattern)
        
        security_patterns = [
            ('csrf', 'CSRF Protection'),
            ('x-csrf-token', 'CSRF Token'),
            ('__RequestVerificationToken', 'Anti-Forgery Token'),
            ('captcha', 'CAPTCHA'),
            ('recaptcha', 'reCAPTCHA'),
            ('two-factor', 'Two-Factor Auth'),
            ('otp', 'OTP Authentication'),
        ]
        
        for pattern, name in security_patterns:
            if pattern.lower() in content.lower() or pattern.lower() in str(headers).lower():
                details['security_features'].append(name)
                confidence_boost += 0.02
        
        return min(confidence_boost, 0.4), details


_detector: Optional[AdvancedDetector] = None


def get_detector() -> AdvancedDetector:
    global _detector
    if _detector is None:
        _detector = AdvancedDetector()
    return _detector


def detect_endpoints(content: str, headers: Dict[str, str], url: str) -> Dict[str, List[EndpointInfo]]:
    return get_detector().detect_all(content, headers, url)


def analyze_admin_potential(content: str, title: str, url: str, headers: Dict[str, str]) -> Tuple[float, Dict]:
    return get_detector().analyze_admin_potential(content, title, url, headers)

"""
IP geolocation service
Supports multiple geolocation API providers, including cache mechanism and local database fallback
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
import time
import ipaddress

logger = logging.getLogger(__name__)


class IPGeolocationService:
    """IP geolocation service"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.cache_duration_hours = 168  # 7 days cache
        self.session = None
        
        # Supported geolocation API providers
        self.providers = {
            'ip-api': {
                'url': 'http://ip-api.com/json/{ip}',
                'rate_limit': 45,  # Requests per minute
                'fields': 'status,message,country,countryCode,region,regionName,city,lat,lon,timezone,isp,org,query'
            },
            'ipapi': {
                'url': 'https://ipapi.co/{ip}/json/',
                'rate_limit': 1000,  # Free requests per day
                'fields': None
            },
            'freegeoip': {
                'url': 'https://freegeoip.app/json/{ip}',
                'rate_limit': 15000,  # Requests per hour
                'fields': None
            }
        }
        
        self.current_provider = 'ip-api'  # Default to ip-api
        self.request_count = 0
        self.last_reset_time = time.time()
        
        # Known cloud service provider IP ranges
        self.cloud_providers = {
            'AWS': ['52.', '54.', '34.', '35.', '18.'],
            'Google Cloud': ['35.', '34.', '130.211.', '104.155.'],
            'Azure': ['52.', '40.', '13.', '104.'],
            'Cloudflare': ['104.16.', '104.17.', '104.18.', '104.19.', '104.20.', '104.21.', '104.22.', '104.23.', '104.24.', '104.25.', '104.26.', '104.27.', '104.28.', '104.29.', '104.30.', '104.31.'],
            'Akamai': ['23.', '184.', '72.'],
            'DigitalOcean': ['128.199.', '159.65.', '167.99.', '206.189.']
        }
    
    def _identify_cloud_provider(self, ip_address: str) -> Optional[str]:
        """Identify cloud service provider"""
        for provider, prefixes in self.cloud_providers.items():
            if any(ip_address.startswith(prefix) for prefix in prefixes):
                return provider
        return None
    
    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if it is a private IP address"""
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private
        except ValueError:
            return False
    
    async def get_session(self):
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=5)  # Reduce timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_location(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get geolocation information for a single IP address"""
        return await self.get_ip_location(ip_address)
    
    async def get_ip_location(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """
        Get geolocation information for an IP address
        Prioritize local database, then check cache, then query API
        """
        try:
            # Check if it is a private IP
            if self._is_private_ip(ip_address):
                return {
                    'ip': ip_address,
                    'country': 'Local Network',
                    'countryCode': 'LN',
                    'region': 'Private',
                    'city': 'Local',
                    'lat': None,
                    'lon': None,
                    'isp': 'Local Network',
                    'org': 'Private Network',
                    'cached': False,
                    'source': 'local_detection'
                }
            
            # Prioritize local reference database
            local_location = await self._query_local_reference_db(ip_address)
            if local_location:
                logger.debug(f"Using local reference database for IP {ip_address}")
                return local_location
            
            # Check old cache
            cached_location = await self._get_cached_location(ip_address)
            if cached_location:
                logger.debug(f"Using cached location for IP {ip_address}")
                return cached_location
            
            # Query API (as a fallback)
            location_data = await self._query_api_location(ip_address)
            if location_data:
                # Store to cache
                await self._cache_location(ip_address, location_data)
                return location_data
            
            # If API query fails, return fallback information based on cloud service provider
            cloud_provider = self._identify_cloud_provider(ip_address)
            if cloud_provider:
                fallback_location = {
                    'ip': ip_address,
                    'country': 'Cloud Service',
                    'countryCode': 'CS',
                    'region': cloud_provider,
                    'city': 'Cloud',
                    'lat': None,
                    'lon': None,
                    'isp': cloud_provider,
                    'org': f'{cloud_provider} Cloud',
                    'cached': False,
                    'source': 'cloud_detection'
                }
                # Cache fallback information
                await self._cache_location(ip_address, fallback_location)
                return fallback_location
            
            # Final fallback
            fallback_location = {
                'ip': ip_address,
                'country': 'Unknown',
                'countryCode': 'UN',
                'region': 'Unknown',
                'city': 'Unknown',
                'lat': None,
                'lon': None,
                'isp': 'Unknown',
                'org': 'Unknown',
                'cached': False,
                'source': 'fallback'
            }
            await self._cache_location(ip_address, fallback_location)
            return fallback_location
            
        except Exception as e:
            logger.error(f"Error getting location for IP {ip_address}: {e}")
            return None
    
    async def _get_cached_location(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get geolocation information from cache"""
        try:
            query = """
            SELECT country_code, country_name, region, city, latitude, longitude, 
                   isp, organization, last_updated
            FROM ip_geolocation_cache 
            WHERE ip_address = $1 
            AND last_updated > $2
            """
            
            cutoff_time = datetime.now() - timedelta(hours=self.cache_duration_hours)
            result = await self.db_manager.execute_query(query, (ip_address, cutoff_time))
            
            if result:
                location = result[0]
                return {
                    'ip': ip_address,
                    'country': location['country_name'],
                    'countryCode': location['country_code'],
                    'region': location['region'],
                    'city': location['city'],
                    'lat': float(location['latitude']) if location['latitude'] else None,
                    'lon': float(location['longitude']) if location['longitude'] else None,
                    'isp': location['isp'],
                    'org': location['organization'],
                    'cached': True
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error reading cached location for {ip_address}: {e}")
            return None
    
    async def _query_local_reference_db(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Query local reference database for geolocation information"""
        try:
            # Use database function to query IP geolocation
            query = "SELECT * FROM lookup_ip_location($1)"
            result = await self.db_manager.execute_query(query, (ip_address,))
            
            if result and result[0]['country_code']:
                location = result[0]
                
                # Convert to standard format
                return {
                    'ip': ip_address,
                    'country': location['country_name'] or 'Unknown',
                    'countryCode': location['country_code'] or 'UN',
                    'region': 'Unknown',  # Local database does not contain region information
                    'city': 'Unknown',    # Local database does not contain city information
                    'lat': None,
                    'lon': None,
                    'isp': location['asn_name'] or 'Unknown',
                    'org': location['asn_name'] or 'Unknown',
                    'asn': location['asn'],
                    'cached': False,
                    'source': 'local_reference_db'
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error querying local reference database for {ip_address}: {e}")
            return None
    
    async def _query_api_location(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Query API for geolocation information, add retry and error handling"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Check rate limit
                if not self._check_rate_limit():
                    logger.warning(f"Rate limit exceeded for provider {self.current_provider}")
                    await asyncio.sleep(retry_delay)
                    continue
                
                session = await self.get_session()
                provider_config = self.providers[self.current_provider]
                url = provider_config['url'].format(ip=ip_address)
                
                if self.current_provider == 'ip-api' and provider_config['fields']:
                    url += f"?fields={provider_config['fields']}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._parse_provider_response(data, ip_address)
                        if result:
                            return result
                    elif response.status == 429:  # Rate limit
                        logger.warning(f"Rate limit hit for {self.current_provider}, attempt {attempt + 1}")
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                    else:
                        logger.warning(f"API request failed with status {response.status}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout querying {self.current_provider} for IP {ip_address}, attempt {attempt + 1}")
                await asyncio.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Error querying API for IP {ip_address}, attempt {attempt + 1}: {e}")
                await asyncio.sleep(retry_delay)
        
        return None
    
    def _standardize_country_name(self, country_name: str) -> str:
        """Enhanced country name standardization with comprehensive mapping"""
        if not country_name:
            return 'Unknown'
        
        # Comprehensive standardization mapping
        standardization_map = {
            # English-speaking countries
            'united states': 'United States',
            'usa': 'United States', 
            'united states of america': 'United States',
            'us': 'United States',
            'united kingdom': 'United Kingdom',
            'uk': 'United Kingdom',
            'great britain': 'United Kingdom',
            'england': 'United Kingdom',
            'scotland': 'United Kingdom',
            'wales': 'United Kingdom',
            'northern ireland': 'United Kingdom',
            'australia': 'Australia',
            'canada': 'Canada',
            'new zealand': 'New Zealand',
            'ireland': 'Ireland',
            'republic of ireland': 'Ireland',
            'south africa': 'South Africa',
            
            # European countries
            'the netherlands': 'Netherlands',
            'netherlands': 'Netherlands',
            'holland': 'Netherlands',
            'germany': 'Germany',
            'deutschland': 'Germany',
            'france': 'France',
            'italia': 'Italy',
            'italy': 'Italy',
            'spain': 'Spain',
            'espana': 'Spain',
            'españa': 'Spain',
            'portugal': 'Portugal',
            'switzerland': 'Switzerland',
            'austria': 'Austria',
            'belgium': 'Belgium',
            'luxembourg': 'Luxembourg',
            'denmark': 'Denmark',
            'sweden': 'Sweden',
            'norway': 'Norway',
            'finland': 'Finland',
            'poland': 'Poland',
            'czech republic': 'Czech Republic',
            'czechia': 'Czech Republic',
            'slovakia': 'Slovakia',
            'hungary': 'Hungary',
            'slovenia': 'Slovenia',
            'croatia': 'Croatia',
            'bosnia and herzegovina': 'Bosnia and Herzegovina',
            'serbia': 'Serbia',
            'montenegro': 'Montenegro',
            'macedonia': 'North Macedonia',
            'north macedonia': 'North Macedonia',
            'albania': 'Albania',
            'greece': 'Greece',
            'bulgaria': 'Bulgaria',
            'romania': 'Romania',
            'lithuania': 'Lithuania',
            'latvia': 'Latvia',
            'estonia': 'Estonia',
            'belarus': 'Belarus',
            'ukraine': 'Ukraine',
            'moldova': 'Moldova',
            'moldova, republic of': 'Moldova',
            'russian federation': 'Russia',
            'russia': 'Russia',
            
            # Asian countries
            'china': 'China',
            'people\'s republic of china': 'China',
            'prc': 'China',
            'japan': 'Japan',
            'south korea': 'South Korea',
            'korea, republic of': 'South Korea',
            'republic of korea': 'South Korea',
            'north korea': 'North Korea',
            'korea, democratic people\'s republic of': 'North Korea',
            'democratic people\'s republic of korea': 'North Korea',
            'india': 'India',
            'pakistan': 'Pakistan',
            'bangladesh': 'Bangladesh',
            'sri lanka': 'Sri Lanka',
            'myanmar': 'Myanmar',
            'burma': 'Myanmar',
            'thailand': 'Thailand',
            'vietnam': 'Vietnam',
            'viet nam': 'Vietnam',
            'cambodia': 'Cambodia',
            'laos': 'Laos',
            'singapore': 'Singapore',
            'malaysia': 'Malaysia',
            'indonesia': 'Indonesia',
            'philippines': 'Philippines',
            'brunei': 'Brunei',
            'taiwan': 'Taiwan',
            'taiwan, province of china': 'Taiwan',
            'hong kong': 'Hong Kong',
            'hong kong sar china': 'Hong Kong',
            'macau': 'Macao',
            'macao': 'Macao',
            'macao sar china': 'Macao',
            
            # Middle Eastern countries
            'iran': 'Iran',
            'iran, islamic republic of': 'Iran',
            'islamic republic of iran': 'Iran',
            'iraq': 'Iraq',
            'afghanistan': 'Afghanistan',
            'turkey': 'Turkey',
            'syria': 'Syria',
            'syrian arab republic': 'Syria',
            'lebanon': 'Lebanon',
            'jordan': 'Jordan',
            'israel': 'Israel',
            'palestine': 'Palestine',
            'palestine, state of': 'Palestine',
            'state of palestine': 'Palestine',
            'saudi arabia': 'Saudi Arabia',
            'united arab emirates': 'United Arab Emirates',
            'uae': 'United Arab Emirates',
            'qatar': 'Qatar',
            'kuwait': 'Kuwait',
            'bahrain': 'Bahrain',
            'oman': 'Oman',
            'yemen': 'Yemen',
            
            # African countries
            'egypt': 'Egypt',
            'libya': 'Libya',
            'tunisia': 'Tunisia',
            'algeria': 'Algeria',
            'morocco': 'Morocco',
            'sudan': 'Sudan',
            'ethiopia': 'Ethiopia',
            'kenya': 'Kenya',
            'uganda': 'Uganda',
            'tanzania': 'Tanzania',
            'tanzania, united republic of': 'Tanzania',
            'united republic of tanzania': 'Tanzania',
            'zimbabwe': 'Zimbabwe',
            'zambia': 'Zambia',
            'botswana': 'Botswana',
            'namibia': 'Namibia',
            'ghana': 'Ghana',
            'nigeria': 'Nigeria',
            'senegal': 'Senegal',
            'mali': 'Mali',
            'burkina faso': 'Burkina Faso',
            'ivory coast': 'Ivory Coast',
            'cote d\'ivoire': 'Ivory Coast',
            'cameroon': 'Cameroon',
            'chad': 'Chad',
            'central african republic': 'Central African Republic',
            'democratic republic of the congo': 'Democratic Republic of the Congo',
            'republic of the congo': 'Republic of the Congo',
            'gabon': 'Gabon',
            'equatorial guinea': 'Equatorial Guinea',
            'madagascar': 'Madagascar',
            
            # South American countries
            'brazil': 'Brazil',
            'argentina': 'Argentina',
            'chile': 'Chile',
            'peru': 'Peru',
            'colombia': 'Colombia',
            'venezuela': 'Venezuela',
            'venezuela, bolivarian republic of': 'Venezuela',
            'bolivarian republic of venezuela': 'Venezuela',
            'ecuador': 'Ecuador',
            'bolivia': 'Bolivia',
            'bolivia, plurinational state of': 'Bolivia',
            'plurinational state of bolivia': 'Bolivia',
            'paraguay': 'Paraguay',
            'uruguay': 'Uruguay',
            'guyana': 'Guyana',
            'suriname': 'Suriname',
            'french guiana': 'French Guiana',
            
            # Special territories and city-states
            'vatican': 'Vatican City',
            'vatican city': 'Vatican City',
            'holy see (vatican city state)': 'Vatican City',
            'holy see': 'Vatican City',
            'monaco': 'Monaco',
            'san marino': 'San Marino',
            'liechtenstein': 'Liechtenstein',
            'andorra': 'Andorra',
            'gibraltar': 'Gibraltar',
            'bermuda': 'Bermuda',
            'puerto rico': 'Puerto Rico',
            'guam': 'Guam',
            'virgin islands': 'Virgin Islands',
            'cayman islands': 'Cayman Islands',
            'bahamas': 'Bahamas',
            'barbados': 'Barbados',
            'jamaica': 'Jamaica',
            'trinidad and tobago': 'Trinidad and Tobago',
            'martinique': 'Martinique',
            'guadeloupe': 'Guadeloupe',
            'aruba': 'Aruba',
            'netherlands antilles': 'Netherlands Antilles',
            'curacao': 'Curacao',
            'curaçao': 'Curacao',
            'saint lucia': 'Saint Lucia',
            'grenada': 'Grenada',
            'dominica': 'Dominica',
            'antigua and barbuda': 'Antigua and Barbuda',
            'saint kitts and nevis': 'Saint Kitts and Nevis',
            'saint vincent and the grenadines': 'Saint Vincent and the Grenadines',
            'dominican republic': 'Dominican Republic',
            'haiti': 'Haiti',
            'cuba': 'Cuba',
            
            # Pacific region
            'fiji': 'Fiji',
            'papua new guinea': 'Papua New Guinea',
            'solomon islands': 'Solomon Islands',
            'vanuatu': 'Vanuatu',
            'new caledonia': 'New Caledonia',
            'french polynesia': 'French Polynesia',
            'samoa': 'Samoa',
            'tonga': 'Tonga',
            'palau': 'Palau',
            'micronesia': 'Micronesia',
            'marshall islands': 'Marshall Islands',
            'kiribati': 'Kiribati',
            'tuvalu': 'Tuvalu',
            'nauru': 'Nauru',
            'cook islands': 'Cook Islands',
            'niue': 'Niue',
            'tokelau': 'Tokelau',
            'american samoa': 'American Samoa',
            'northern mariana islands': 'Northern Mariana Islands',
            
            # Other regions
            'greenland': 'Greenland',
            'iceland': 'Iceland',
            'faroe islands': 'Faroe Islands',
            'åland islands': 'Åland Islands',
            'aland islands': 'Åland Islands',
            'svalbard and jan mayen': 'Svalbard and Jan Mayen',
            'isle of man': 'Isle of Man',
            'jersey': 'Jersey',
            'guernsey': 'Guernsey',
            'falkland islands': 'Falkland Islands',
            'south georgia and the south sandwich islands': 'South Georgia and the South Sandwich Islands',
            'british indian ocean territory': 'British Indian Ocean Territory',
            'christmas island': 'Christmas Island',
            'cocos islands': 'Cocos Islands',
            'norfolk island': 'Norfolk Island',
            'heard island and mcdonald islands': 'Heard Island and McDonald Islands',
            'antarctica': 'Antarctica',
            'bouvet island': 'Bouvet Island',
            'french southern territories': 'French Southern Territories',
            'mayotte': 'Mayotte',
            'reunion': 'Reunion',
            'réunion': 'Reunion',
            'saint helena': 'Saint Helena',
            'ascension and tristan da cunha': 'Ascension and Tristan da Cunha',
            'western sahara': 'Western Sahara',
            'pitcairn': 'Pitcairn',
            'turks and caicos islands': 'Turks and Caicos Islands',
            'british virgin islands': 'British Virgin Islands',
            'anguilla': 'Anguilla',
            'montserrat': 'Montserrat',
            'saint pierre and miquelon': 'Saint Pierre and Miquelon',
            'wallis and futuna': 'Wallis and Futuna',
            'saint martin': 'Saint Martin',
            'sint maarten': 'Sint Maarten',
            'saint barthelemy': 'Saint Barthelemy',
            'saint barthélemy': 'Saint Barthelemy'
        }
        
        # Convert to lowercase for matching
        country_lower = country_name.lower().strip()
        
        # If found in standardization map, return standardized name
        if country_lower in standardization_map:
            return standardization_map[country_lower]
        
        # Otherwise return original name (first letter capitalized)
        return country_name.title()
    
    def _parse_provider_response(self, data: Dict[str, Any], ip_address: str) -> Optional[Dict[str, Any]]:
        """Parse response format from different API providers"""
        try:
            if self.current_provider == 'ip-api':
                if data.get('status') == 'success':
                    raw_country = data.get('country', 'Unknown')
                    standardized_country = self._standardize_country_name(raw_country)
                    return {
                        'ip': ip_address,
                        'country': standardized_country,
                        'countryCode': data.get('countryCode', 'UN'),
                        'region': data.get('regionName', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'lat': data.get('lat'),
                        'lon': data.get('lon'),
                        'isp': data.get('isp', 'Unknown'),
                        'org': data.get('org', 'Unknown'),
                        'cached': False
                    }
                else:
                    logger.warning(f"API returned error for {ip_address}: {data.get('message', 'Unknown error')}")
                    return None
            
            elif self.current_provider == 'ipapi':
                if 'error' not in data:
                    raw_country = data.get('country_name', 'Unknown')
                    standardized_country = self._standardize_country_name(raw_country)
                    return {
                        'ip': ip_address,
                        'country': standardized_country,
                        'countryCode': data.get('country', 'UN'),
                        'region': data.get('region', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'lat': data.get('latitude'),
                        'lon': data.get('longitude'),
                        'isp': data.get('org', 'Unknown'),
                        'org': data.get('org', 'Unknown'),
                        'cached': False
                    }
            
            elif self.current_provider == 'freegeoip':
                raw_country = data.get('country_name', 'Unknown')
                standardized_country = self._standardize_country_name(raw_country)
                return {
                    'ip': ip_address,
                    'country': standardized_country,
                    'countryCode': data.get('country_code', 'UN'),
                    'region': data.get('region_name', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                    'isp': 'Unknown',
                    'org': 'Unknown',
                    'cached': False
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing provider response: {e}")
            return None
    
    async def _cache_location(self, ip_address: str, location_data: Dict[str, Any]):
        """Cache geolocation information to database"""
        try:
            query = """
            INSERT INTO ip_geolocation_cache 
            (ip_address, country_code, country_name, region, city, latitude, longitude, isp, organization)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (ip_address) 
            DO UPDATE SET
                country_code = EXCLUDED.country_code,
                country_name = EXCLUDED.country_name,
                region = EXCLUDED.region,
                city = EXCLUDED.city,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                isp = EXCLUDED.isp,
                organization = EXCLUDED.organization,
                last_updated = CURRENT_TIMESTAMP
            """
            
            await self.db_manager.execute_command(query, (
                ip_address,
                location_data.get('countryCode', 'UN'),
                location_data.get('country', 'Unknown'),
                location_data.get('region', 'Unknown'),
                location_data.get('city', 'Unknown'),
                location_data.get('lat'),
                location_data.get('lon'),
                location_data.get('isp', 'Unknown'),
                location_data.get('org', 'Unknown')
            ))
            
            logger.debug(f"Cached location data for IP {ip_address}")
            
        except Exception as e:
            logger.error(f"Error caching location for IP {ip_address}: {e}")
    
    def _check_rate_limit(self) -> bool:
        """Check API call rate limit"""
        current_time = time.time()
        
        # Reset counter (per minute)
        if current_time - self.last_reset_time > 60:
            self.request_count = 0
            self.last_reset_time = current_time
        
        provider_config = self.providers[self.current_provider]
        rate_limit = provider_config['rate_limit']
        
        if self.request_count >= rate_limit:
            return False
        
        self.request_count += 1
        return True
    
    async def bulk_get_locations(self, ip_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """Bulk get geolocation information for multiple IP addresses, optimize performance"""
        if not ip_addresses:
            return {}
        
        results = {}
        
        # Deduplicate and filter private IPs
        unique_ips = list(set(ip_addresses))
        public_ips = []
        
        # Fast processing of private IPs and known patterns
        for ip in unique_ips:
            if self._is_private_ip(ip):
                results[ip] = {
                    'ip': ip,
                    'country': 'Local Network',
                    'countryCode': 'LN',
                    'region': 'Private',
                    'city': 'Local',
                    'lat': None,
                    'lon': None,
                    'isp': 'Local Network',
                    'org': 'Private Network',
                    'cached': False,
                    'source': 'local_detection'
                }
            elif ip in ['8.8.8.8', '8.8.4.4', '1.1.1.1', '1.0.0.1']:
                # Fast processing of known DNS servers
                results[ip] = {
                    'ip': ip,
                    'country': 'United States',
                    'countryCode': 'US',
                    'region': 'DNS Service',
                    'city': 'DNS',
                    'lat': None,
                    'lon': None,
                    'isp': 'DNS Provider',
                    'org': 'Public DNS',
                    'cached': False,
                    'source': 'known_service'
                }
            else:
                # Check cloud service provider
                cloud_provider = self._identify_cloud_provider(ip)
                if cloud_provider:
                    results[ip] = {
                        'ip': ip,
                        'country': 'Cloud Service',
                        'countryCode': 'CS',
                        'region': cloud_provider,
                        'city': 'Cloud',
                        'lat': None,
                        'lon': None,
                        'isp': cloud_provider,
                        'org': f'{cloud_provider} Cloud',
                        'cached': False,
                        'source': 'cloud_detection'
                    }
                else:
                    public_ips.append(ip)
        
        if not public_ips:
            return results
        
        # Batch query cache - cache query
        cached_results = await self._batch_get_cached_locations(public_ips)
        results.update(cached_results)
        
        # Get IPs that need to query API
        uncached_ips = [ip for ip in public_ips if ip not in results]
        
        if uncached_ips and len(uncached_ips) <= 100:  # Only query API when there are few IPs
            # Significantly optimized concurrent processing
            semaphore = asyncio.Semaphore(15)  # Increase concurrency
            
            async def get_single_location(ip):
                async with semaphore:
                    location = await self.get_ip_location(ip)
                    if location:
                        results[ip] = location
                    # Remove unnecessary delay
            
            # Larger batch
            batch_size = 50
            for i in range(0, len(uncached_ips), batch_size):
                batch = uncached_ips[i:i+batch_size]
                tasks = [get_single_location(ip) for ip in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Reduce batch delay
                if i + batch_size < len(uncached_ips):
                    await asyncio.sleep(0.3)  # Reduce from 1 second to 0.3 seconds
        else:
            # For large number of IPs, use fallback fast scheme
            logger.info(f"Using fallback for {len(uncached_ips)} uncached IPs to improve performance")
            for ip in uncached_ips:
                results[ip] = {
                    'ip': ip,
                    'country': 'Internet',
                    'countryCode': 'IN',
                    'region': 'External',
                    'city': 'Internet',
                    'lat': None,
                    'lon': None,
                    'isp': 'Internet Service',
                    'org': 'External Network',
                    'cached': False,
                    'source': 'fallback_fast'
                }
        
        return results
    
    async def _batch_get_cached_locations(self, ip_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch get cached geolocation information"""
        if not ip_addresses:
            return {}
        
        try:
            # Build IN query
            ip_placeholders = ','.join(f'${i+1}' for i in range(len(ip_addresses)))
            query = f"""
            SELECT ip_address, country_code, country_name, region, city, 
                   latitude, longitude, isp, organization, last_updated
            FROM ip_geolocation_cache 
            WHERE ip_address IN ({ip_placeholders})
            AND last_updated > ${len(ip_addresses) + 1}
            """
            
            cutoff_time = datetime.now() - timedelta(hours=self.cache_duration_hours)
            params = tuple(ip_addresses) + (cutoff_time,)
            
            result = await self.db_manager.execute_query(query, params)
            
            cached_results = {}
            for row in result:
                ip_address = row['ip_address']
                cached_results[ip_address] = {
                    'ip': ip_address,
                    'country': row['country_name'],
                    'countryCode': row['country_code'],
                    'region': row['region'],
                    'city': row['city'],
                    'lat': float(row['latitude']) if row['latitude'] else None,
                    'lon': float(row['longitude']) if row['longitude'] else None,
                    'isp': row['isp'],
                    'org': row['organization'],
                    'cached': True
                }
            
            return cached_results
            
        except Exception as e:
            logger.error(f"Error batch reading cached locations: {e}")
            return {}
    
    async def get_location_statistics(self, experiment_id: str) -> Dict[str, Any]:
        """Get geolocation statistics for all IPs in an experiment"""
        try:
            # Get all unique IPs in the experiment
            query = """
            SELECT DISTINCT dst_ip as ip_address
            FROM packet_flows 
            WHERE experiment_id = $1 
            AND dst_ip IS NOT NULL 
            AND dst_ip != '0.0.0.0'::inet
            AND NOT (HOST(dst_ip) LIKE '192.168.%' OR HOST(dst_ip) LIKE '10.%' OR HOST(dst_ip) LIKE '172.%')
            """
            
            result = await self.db_manager.execute_query(query, (experiment_id,))
            unique_ips = [row['ip_address'] for row in result]
            
            # Batch get geolocation information
            locations = await self.bulk_get_locations(unique_ips)
            
            # Count country distribution
            country_stats = {}
            city_stats = {}
            total_ips = len(unique_ips)
            located_ips = len(locations)
            
            for ip, location in locations.items():
                country = location.get('country', 'Unknown')
                city = location.get('city', 'Unknown')
                
                country_stats[country] = country_stats.get(country, 0) + 1
                city_key = f"{city}, {country}"
                city_stats[city_key] = city_stats.get(city_key, 0) + 1
            
            return {
                'total_unique_ips': total_ips,
                'located_ips': located_ips,
                'location_coverage': (located_ips / total_ips * 100) if total_ips > 0 else 0,
                'country_distribution': dict(sorted(country_stats.items(), key=lambda x: x[1], reverse=True)),
                'city_distribution': dict(sorted(city_stats.items(), key=lambda x: x[1], reverse=True)[:20])  # Top 20 cities
            }
            
        except Exception as e:
            logger.error(f"Error getting location statistics for experiment {experiment_id}: {e}")
            return {
                'total_unique_ips': 0,
                'located_ips': 0,
                'location_coverage': 0,
                'country_distribution': {},
                'city_distribution': {}
            } 
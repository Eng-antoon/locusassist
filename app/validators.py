import requests
import json
import logging
import time
import base64
import re
import difflib
from datetime import datetime
from models import ValidationResult, db

logger = logging.getLogger(__name__)

class GS1Validator:
    def __init__(self):
        pass

    def get_product_info(self, gtin):
        """Fetch product information from GS1 Verified database"""
        try:
            logger.info(f"Fetching GS1 product info for GTIN: {gtin}")

            # GS1 Verified API endpoint
            url = "https://www.gs1.org/services/verified-by-gs1/results"

            headers = {
                "accept": "application/json, text/javascript, */*; q=0.01",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest"
            }

            # Prepare form data for GTIN search
            form_data = {
                "search_type": "gtin",
                "gtin": gtin,
                "gln": "",
                "country": "",
                "street_address": "",
                "postal_code": "",
                "city": "",
                "company_name": "",
                "other_key_type": "",
                "other_key": "",
                "_triggering_element_name": "gtin_submit",
                "_triggering_element_value": "Search",
                "_drupal_ajax": "1"
            }

            # Make the request
            response = requests.post(url, headers=headers, data=form_data, timeout=10)

            if response.status_code == 200:
                result = response.json()

                # Parse the response to extract product information
                product_info = self.parse_gs1_response(result, gtin)
                return product_info
            else:
                logger.error(f"GS1 API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching GS1 data for GTIN {gtin}: {e}")
            return None

    def parse_gs1_response(self, response_data, gtin):
        """Parse GS1 API response to extract product information"""
        try:
            # Look for the HTML content in the response
            for item in response_data:
                if item.get('command') == 'insert' and 'data' in item:
                    html_content = item['data']

                    # Extract product information using regex or HTML parsing
                    # Extract product name
                    product_name_match = re.search(r'<h3[^>]*>([^<]+)</h3>', html_content)
                    product_name = product_name_match.group(1).strip() if product_name_match else None

                    # Extract brand names (both Arabic and English)
                    brand_names = {}
                    # English brand name
                    brand_en_match = re.search(r'Brand name.*?<strong[^>]*>\(en\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if brand_en_match:
                        brand_names['english'] = brand_en_match.group(1).strip()

                    # Arabic brand name
                    brand_ar_match = re.search(r'Brand name.*?<strong[^>]*>\(ar\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if brand_ar_match:
                        brand_names['arabic'] = brand_ar_match.group(1).strip()

                    # Extract product descriptions (both languages)
                    product_names = {}
                    # English product description
                    product_en_match = re.search(r'Product description.*?<strong[^>]*>\(en\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if product_en_match:
                        product_names['english'] = product_en_match.group(1).strip()

                    # Arabic product description
                    product_ar_match = re.search(r'Product description.*?<strong[^>]*>\(ar\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if product_ar_match:
                        product_names['arabic'] = product_ar_match.group(1).strip()

                    # If no bilingual match, try single product name
                    if not product_names and product_name:
                        product_names['primary'] = product_name

                    # Extract company name
                    company_match = re.search(r'registered to.*?<strong[^>]*>([^<]+)</strong>', html_content)
                    company_name = company_match.group(1).strip() if company_match else None

                    # Extract product category
                    category_match = re.search(r'Global product category.*?<strong[^>]*>([^<]+)</strong>', html_content)
                    category = category_match.group(1).strip() if category_match else None

                    # Extract net content
                    content_match = re.search(r'Net content.*?<strong[^>]*>([^<]+)</strong>', html_content)
                    net_content = content_match.group(1).strip() if content_match else None

                    if product_names or brand_names:
                        return {
                            'gtin': gtin,
                            'product_names': product_names,
                            'brand_names': brand_names,
                            'product_name': product_names.get('english') or product_names.get('primary') or '',  # For backward compatibility
                            'brand_name': brand_names.get('english') or '',  # For backward compatibility
                            'company_name': company_name,
                            'category': category,
                            'net_content': net_content,
                            'verified': True
                        }

            return None

        except Exception as e:
            logger.error(f"Error parsing GS1 response: {e}")
            return None

class GoogleAIValidator:
    def __init__(self, config=None):
        if config:
            self.api_key = config.GOOGLE_AI_API_KEY
            self.api_url = config.GOOGLE_AI_API_URL
            self.bearer_token = config.BEARER_TOKEN
        else:
            # Fallback to environment variables
            import os
            self.api_key = os.getenv('GOOGLE_AI_API_KEY')
            self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
            self.bearer_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg3ODkzNDcsImV4cCI6MTc1ODgzMjU0Nywic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.kuies9vwY2S8FHpgBzFKKfvl2v0St2DpPfJEQ5KO6Tyhjf9_ORx3fZMkpc5fKo39d-yAz5G0x8xvcaQynPQJ8NAhpC9xErOW0bD2d3Soy8BmKOafoJkHHB7m-LnsJZMjyHhqEYzE8lsvPSHkLQkRoXjmWBrHJicshf1qPbs6DdM_XSneSfXUK8B1wJxyoRTFs2F_rD44WXdBmWuZsu8xn-rW6wGNtNXjwjBhsGiKhO1EN5BrVgv-X0px60pSRNxgdul-77D9vIx_Wj8ev5WwUXL_B3qNU5JQMDUd_Az1JvR_etQg2NogjN_V-n5vsqJEZUismpfp-qXqp39pPp3jwQ"

        self.gs1_validator = GS1Validator()

        # UoM conversion mappings
        self.uom_conversions = {
            'box': ['boxes', 'carton', 'cartons', 'case', 'cases'],
            'unit': ['units', 'piece', 'pieces', 'pcs', 'pc'],
            'kg': ['kilogram', 'kilograms', 'kilo', 'kilos'],
            'g': ['gram', 'grams', 'gm'],
            'l': ['liter', 'liters', 'litre', 'litres'],
            'ml': ['milliliter', 'milliliters', 'millilitre', 'millilitres']
        }

        # Common package multipliers
        self.package_patterns = {
            r'\((\d+)\+(\d+)\)\*(\d+)': lambda m: (int(m[1]) + int(m[2])) * int(m[3]),  # (5+1)*4
            r'(\d+)\*(\d+)': lambda m: int(m[1]) * int(m[2]),  # 2*10
            r'(\d+)x(\d+)': lambda m: int(m[1]) * int(m[2]),  # 6x12
        }

    def normalize_unit(self, unit_str):
        """Normalize unit of measurement to standard form"""
        if not unit_str:
            return 'unit'

        unit_lower = unit_str.lower().strip()

        for standard_unit, variations in self.uom_conversions.items():
            if unit_lower == standard_unit or unit_lower in variations:
                return standard_unit

        return unit_lower

    def parse_package_quantity(self, quantity_str):
        """Parse package configuration strings like (5+1)*4 to calculate total quantity"""
        if not quantity_str:
            return None, None

        quantity_str = str(quantity_str).strip()

        # Try to extract just the number first
        number_match = re.search(r'(\d+(?:\.\d+)?)', quantity_str)
        base_quantity = float(number_match.group(1)) if number_match else 0

        # Try package patterns
        for pattern, calculator in self.package_patterns.items():
            match = re.search(pattern, quantity_str)
            if match:
                calculated_qty = calculator(match)
                logger.info(f"Parsed package '{quantity_str}' -> {calculated_qty} units")
                return calculated_qty, 'calculated'

        return base_quantity, 'direct'

    def convert_quantity_units(self, from_qty, from_unit, to_unit, product_context=None):
        """Convert quantities between different units of measurement"""
        try:
            from_unit_norm = self.normalize_unit(from_unit)
            to_unit_norm = self.normalize_unit(to_unit)

            if from_unit_norm == to_unit_norm:
                return from_qty, 1.0  # Same unit, no conversion needed

            # Handle box to unit conversions (common case)
            if from_unit_norm == 'box' and to_unit_norm == 'unit':
                # Try to infer items per box from product context or use common ratios
                if product_context:
                    # Look for patterns in product name/sku that might indicate pack size
                    pack_matches = re.findall(r'(\d+)(?:x|X|\*)(\d+)', str(product_context))
                    if pack_matches:
                        pack_size = int(pack_matches[0][0]) * int(pack_matches[0][1])
                        return from_qty * pack_size, pack_size

                # Default assumptions for common products
                default_multiplier = 12  # Assume 12 units per box as common
                logger.warning(f"Using default box->unit conversion: 1 box = {default_multiplier} units")
                return from_qty * default_multiplier, default_multiplier

            elif from_unit_norm == 'unit' and to_unit_norm == 'box':
                # Reverse conversion
                default_divisor = 12
                return from_qty / default_divisor, 1/default_divisor

            # Weight conversions
            elif from_unit_norm == 'kg' and to_unit_norm == 'g':
                return from_qty * 1000, 1000
            elif from_unit_norm == 'g' and to_unit_norm == 'kg':
                return from_qty / 1000, 1/1000

            # Volume conversions
            elif from_unit_norm == 'l' and to_unit_norm == 'ml':
                return from_qty * 1000, 1000
            elif from_unit_norm == 'ml' and to_unit_norm == 'l':
                return from_qty / 1000, 1/1000

            # If no conversion available, return original with note
            logger.warning(f"No conversion available from {from_unit} to {to_unit}")
            return from_qty, None

        except Exception as e:
            logger.error(f"Error converting {from_qty} {from_unit} to {to_unit}: {e}")
            return from_qty, None

    def validate_quantities_with_uom(self, validation_data, order_items):
        """Enhanced quantity validation with UoM conversion support"""
        try:
            logger.info("Starting enhanced quantity validation with UoM support")

            extracted_items = validation_data.get('extracted_items', [])
            enhanced_discrepancies = list(validation_data.get('discrepancies', []))
            conversions_attempted = 0
            successful_conversions = 0

            for extracted_item in extracted_items:
                matched_sku = extracted_item.get('matched_order_sku')
                if not matched_sku:
                    continue

                # Find corresponding order item
                order_item = next((item for item in order_items if item['sku_id'] == matched_sku), None)
                if not order_item:
                    continue

                extracted_qty = extracted_item.get('extracted_quantity', 0)
                extracted_unit = extracted_item.get('extracted_unit', 'unit')
                order_qty = order_item.get('quantity', 0)
                order_unit = order_item.get('unit', 'unit')

                # Parse package configurations if present
                package_config = extracted_item.get('package_config')
                if package_config:
                    parsed_qty, parse_method = self.parse_package_quantity(package_config)
                    if parsed_qty:
                        extracted_qty = parsed_qty
                        logger.info(f"Used package configuration: {package_config} -> {parsed_qty}")

                # Try UoM conversion
                converted_qty = extracted_qty
                conversion_ratio = None

                try:
                    converted_qty, conversion_ratio = self.convert_quantity_units(
                        float(extracted_qty),
                        extracted_unit,
                        order_unit,
                        product_context=f"{order_item.get('name', '')} {matched_sku}"
                    )
                    conversions_attempted += 1

                    if conversion_ratio is not None:
                        logger.info(f"UoM conversion: {extracted_qty} {extracted_unit} -> {converted_qty} {order_unit} (ratio: {conversion_ratio})")
                except Exception as e:
                    logger.error(f"UoM conversion failed: {e}")

                # Check for quantity match after conversion
                order_qty_float = float(order_qty)
                tolerance = max(1, order_qty_float * 0.05)  # 5% tolerance or minimum 1 unit

                if abs(converted_qty - order_qty_float) <= tolerance:
                    # Quantities match within tolerance
                    extracted_item['quantity_equivalent'] = converted_qty
                    extracted_item['status'] = 'MATCHED'
                    if conversion_ratio:
                        successful_conversions += 1
                else:
                    # Quantity mismatch
                    extracted_item['status'] = 'QUANTITY_MISMATCH'

                    # Determine severity
                    percentage_diff = abs(converted_qty - order_qty_float) / order_qty_float * 100
                    if percentage_diff > 20:
                        severity = 'HIGH'
                    elif percentage_diff > 10:
                        severity = 'MEDIUM'
                    else:
                        severity = 'LOW'

                    enhanced_discrepancies.append({
                        'type': 'QUANTITY_MISMATCH',
                        'description': f'Quantity mismatch for {matched_sku}',
                        'expected': f'{order_qty} {order_unit}',
                        'actual': f'{extracted_qty} {extracted_unit}' + (f' (≈{converted_qty:.1f} {order_unit})' if conversion_ratio else ''),
                        'sku_id': matched_sku,
                        'severity': severity,
                        'percentage_diff': round(percentage_diff, 1)
                    })

            # Update validation data
            validation_data['discrepancies'] = enhanced_discrepancies
            validation_data['uom_analysis'] = {
                'conversions_attempted': conversions_attempted,
                'successful_conversions': successful_conversions,
                'unresolved_uom_issues': conversions_attempted - successful_conversions
            }

            logger.info(f"UoM validation complete: {successful_conversions}/{conversions_attempted} successful conversions")
            return validation_data

        except Exception as e:
            logger.error(f"Error in UoM validation: {e}")
            return validation_data

    def download_image(self, image_url):
        """Download image from URL and convert to base64"""
        try:
            logger.info(f"Attempting to download image from: {image_url}")

            headers = {
                "authorization": f"Bearer {self.bearer_token}",
                "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "accept": "*/*"
            }

            response = requests.get(image_url, headers=headers, timeout=30)
            logger.info(f"Image download response status: {response.status_code}")

            response.raise_for_status()

            # Check if we got actual image content
            if not response.content:
                logger.error("Downloaded content is empty")
                return None, None

            logger.info(f"Downloaded image size: {len(response.content)} bytes")

            # Convert to base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')

            # Detect image format from content-type header or URL
            image_format = 'jpeg'  # default
            content_type = response.headers.get('content-type', '').lower()

            if 'png' in content_type or image_url.lower().endswith('.png'):
                image_format = 'png'
            elif 'pdf' in content_type or image_url.lower().endswith('.pdf'):
                image_format = 'pdf'
            elif 'jpeg' in content_type or 'jpg' in content_type or image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                image_format = 'jpeg'

            logger.info(f"Detected image format: {image_format}")
            return image_base64, image_format

        except requests.RequestException as e:
            logger.error(f"HTTP error downloading image from {image_url}: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error downloading image from {image_url}: {e}")
            return None, None

    def fix_json_response(self, json_str):
        """Fix common JSON formatting issues in AI responses"""
        try:
            # First, try to find where the JSON might be truncated
            # Look for incomplete strings or objects

            # Remove any trailing incomplete content
            lines = json_str.split('\n')
            fixed_lines = []

            for i, line in enumerate(lines):
                # Skip empty lines
                if not line.strip():
                    continue

                # Check if this line starts a string but doesn't end it properly
                if '"' in line:
                    quote_count = line.count('"')
                    # If odd number of quotes, the string might be incomplete
                    if quote_count % 2 == 1 and i == len(lines) - 1:
                        # This is likely an incomplete string at the end
                        break

                fixed_lines.append(line)

            json_str = '\n'.join(fixed_lines)

            # Try to find the last complete JSON object/array
            brace_count = 0
            bracket_count = 0
            in_string = False
            escape_next = False
            last_complete_pos = -1

            for i, char in enumerate(json_str):
                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1

                # If we have balanced braces/brackets, this might be a complete JSON
                if brace_count == 0 and bracket_count == 0 and char in '}]':
                    last_complete_pos = i

            if last_complete_pos > -1:
                json_str = json_str[:last_complete_pos + 1]

            # Additional cleanup - don't replace newlines in JSON strings as it corrupts them

            # Fix common Unicode issues
            json_str = json_str.encode('utf-8', errors='replace').decode('utf-8')

            return json_str

        except Exception as e:
            logger.error(f"Error fixing JSON response: {e}")
            return json_str

    def create_fallback_response(self, partial_response):
        """Create a fallback response when JSON parsing fails"""
        try:
            # Try to extract key information using regex
            validation_result = "INVALID"
            confidence_score = 0.5
            discrepancies = []
            summary = {}

            # Look for validation result
            if "VALID" in partial_response.upper():
                if "INVALID" in partial_response.upper():
                    validation_result = "INVALID"
                else:
                    validation_result = "VALID"

            # Try to extract confidence score
            confidence_match = re.search(r'"confidence_score":\s*([0-9.]+)', partial_response)
            if confidence_match:
                try:
                    confidence_score = float(confidence_match.group(1))
                except ValueError:
                    pass

            # Try to extract discrepancies from partial text
            discrepancy_patterns = [
                r'"type":\s*"([^"]+)"[^}]*"description":\s*"([^"]+)"',
                r'"description":\s*"([^"]+)"[^}]*"type":\s*"([^"]+)"'
            ]

            for pattern in discrepancy_patterns:
                matches = re.findall(pattern, partial_response)
                for match in matches:
                    if len(match) == 2:
                        if 'type' in pattern and pattern.index('type') < pattern.index('description'):
                            discrepancies.append({
                                "type": match[0],
                                "description": match[1]
                            })
                        else:
                            discrepancies.append({
                                "type": match[1],
                                "description": match[0]
                            })

            # Try to extract summary counts
            total_items_match = re.search(r'"total_items_found":\s*([0-9]+)', partial_response)
            expected_items_match = re.search(r'"total_items_expected":\s*([0-9]+)', partial_response)
            matched_items_match = re.search(r'"items_matched":\s*([0-9]+)', partial_response)

            if total_items_match or expected_items_match or matched_items_match:
                summary = {
                    "total_items_found": int(total_items_match.group(1)) if total_items_match else 0,
                    "total_items_expected": int(expected_items_match.group(1)) if expected_items_match else 0,
                    "items_matched": int(matched_items_match.group(1)) if matched_items_match else 0,
                    "items_with_discrepancies": len(discrepancies)
                }

            # Only return fallback if we extracted something useful
            if discrepancies or summary:
                logger.info(f"Created fallback response with {len(discrepancies)} discrepancies")
                return {
                    'success': True,
                    'is_valid': validation_result == 'VALID',
                    'confidence_score': confidence_score,
                    'discrepancies': discrepancies,
                    'summary': summary,
                    'ai_response': partial_response,
                    'fallback': True
                }

            return None

        except Exception as e:
            logger.error(f"Error creating fallback response: {e}")
            return None

    def normalize_text_for_matching(self, text):
        """Advanced text normalization for better Arabic/English matching"""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower().strip()

        # Remove common Arabic diacritics
        arabic_diacritics = "ًٌٍَُِّْ"
        for diacritic in arabic_diacritics:
            text = text.replace(diacritic, "")

        # Normalize common Arabic letter variations
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ة", "ه")  # Ta marbuta to ha
        text = text.replace("ي", "ى")  # Alif maksura normalization

        # Remove punctuation and special characters but keep Arabic and alphanumeric
        text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)

        # Normalize whitespace
        text = ' '.join(text.split())

        return text

    def extract_meaningful_words(self, text):
        """Extract meaningful words, filtering out common stopwords"""
        if not text:
            return set()

        # Arabic stopwords (common ones)
        arabic_stopwords = {'من', 'في', 'على', 'إلى', 'مع', 'هذا', 'هذه', 'ذلك', 'التي', 'الذي', 'كل', 'بعض'}

        # English stopwords (common ones)
        english_stopwords = {'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'a', 'an'}

        words = set(text.split())

        # Filter out stopwords and very short words (but keep 2-letter words for Arabic)
        meaningful_words = {word for word in words
                          if len(word) > 1 and
                          word not in arabic_stopwords and
                          word not in english_stopwords}

        return meaningful_words

    def calculate_bilingual_match(self, extracted_name, gs1_product):
        """Advanced bilingual matching for Arabic/English product names"""
        try:
            if not extracted_name or not gs1_product:
                return False, 0.0

            # Use advanced normalization
            extracted_name_normalized = self.normalize_text_for_matching(extracted_name)

            # Get all possible names to match against
            match_candidates = []

            # Add all GS1 names
            product_names = gs1_product.get('product_names', {})
            brand_names = gs1_product.get('brand_names', {})

            # Add English names with normalization
            if product_names.get('english'):
                match_candidates.append(('product_en', self.normalize_text_for_matching(product_names['english'])))
            if brand_names.get('english'):
                match_candidates.append(('brand_en', self.normalize_text_for_matching(brand_names['english'])))

            # Add Arabic names with normalization
            if product_names.get('arabic'):
                match_candidates.append(('product_ar', self.normalize_text_for_matching(product_names['arabic'])))
            if brand_names.get('arabic'):
                match_candidates.append(('brand_ar', self.normalize_text_for_matching(brand_names['arabic'])))

            # Add primary name for backward compatibility
            if product_names.get('primary'):
                match_candidates.append(('primary', self.normalize_text_for_matching(product_names['primary'])))

            # Add backward compatibility names
            if gs1_product.get('product_name'):
                match_candidates.append(('legacy_product', self.normalize_text_for_matching(gs1_product['product_name'])))
            if gs1_product.get('brand_name'):
                match_candidates.append(('legacy_brand', self.normalize_text_for_matching(gs1_product['brand_name'])))

            logger.info(f"Matching '{extracted_name}' against {len(match_candidates)} candidates")

            best_match = None
            best_score = 0.0

            for match_type, candidate_name in match_candidates:
                if not candidate_name:
                    continue

                # Exact match (highest score)
                if extracted_name_normalized == candidate_name:
                    logger.info(f"EXACT normalized match found: '{extracted_name}' == '{candidate_name}' ({match_type})")
                    return True, 1.0

                # Advanced word-based matching using meaningful words
                extracted_words = self.extract_meaningful_words(extracted_name_normalized)
                candidate_words = self.extract_meaningful_words(candidate_name)

                if extracted_words and candidate_words:
                    # Jaccard similarity (intersection over union)
                    intersection = len(extracted_words & candidate_words)
                    union = len(extracted_words | candidate_words)
                    jaccard_score = intersection / union if union > 0 else 0

                    # Containment score (how much of extracted is in candidate)
                    containment_score = intersection / len(extracted_words) if len(extracted_words) > 0 else 0

                    # Combined score with bias towards containment
                    combined_score = (jaccard_score * 0.6) + (containment_score * 0.4)

                    logger.info(f"Word match: '{extracted_name}' vs '{candidate_name}' ({match_type}) = {combined_score:.3f}")

                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = (match_type, candidate_name)

                # Fuzzy string matching using difflib on normalized text
                similarity = difflib.SequenceMatcher(None, extracted_name_normalized, candidate_name).ratio()
                logger.info(f"String similarity: '{extracted_name}' vs '{candidate_name}' ({match_type}) = {similarity:.3f}")

                if similarity > best_score:
                    best_score = similarity
                    best_match = (match_type, candidate_name)

            # Dynamic threshold based on content language mix
            # More lenient for mixed Arabic/English content
            has_arabic = any('\u0600' <= char <= '\u06FF' for char in extracted_name)
            has_english = any(char.isascii() and char.isalpha() for char in extracted_name)

            if has_arabic and has_english:
                threshold = 0.55  # More lenient for mixed content
            elif has_arabic:
                threshold = 0.6   # Standard for Arabic
            else:
                threshold = 0.65  # Slightly stricter for English-only
            is_match = best_score >= threshold

            if best_match:
                logger.info(f"Best match for '{extracted_name}': {best_match[1]} ({best_match[0]}) with score {best_score:.3f} (threshold: {threshold:.2f}) - {'MATCH' if is_match else 'NO MATCH'}")
            else:
                logger.info(f"No good match found for '{extracted_name}' (best score: {best_score:.3f}, threshold: {threshold:.2f})")

            return is_match, best_score

        except Exception as e:
            logger.error(f"Error in bilingual matching: {e}")
            return False, 0.0

    def enhance_with_gtin_verification(self, validation_data):
        """Enhance validation results with GS1 GTIN verification"""
        try:
            logger.info("Starting GTIN verification enhancement")

            # Get extracted items from validation data
            extracted_items = validation_data.get('extracted_items', [])
            gtin_verification = []
            enhanced_discrepancies = list(validation_data.get('discrepancies', []))

            for item in extracted_items:
                gtin = item.get('extracted_gtin')
                if gtin and len(str(gtin)) == 13:
                    logger.info(f"Verifying GTIN: {gtin}")

                    # Get product info from GS1
                    gs1_product = self.gs1_validator.get_product_info(str(gtin))

                    gtin_verification_item = {
                        'gtin': gtin,
                        'extracted_name': item.get('extracted_name', ''),
                        'gs1_verified': gs1_product is not None,
                        'gs1_product_info': gs1_product
                    }

                    if gs1_product:
                        # Use advanced bilingual matching
                        extracted_name = item.get('extracted_name', '')
                        name_match, match_confidence = self.calculate_bilingual_match(extracted_name, gs1_product)

                        gtin_verification_item['name_match'] = name_match
                        gtin_verification_item['match_confidence'] = match_confidence

                        # Add discrepancy if names don't match
                        if not name_match:
                            enhanced_discrepancies.append({
                                'type': 'GTIN_NAME_MISMATCH',
                                'description': f'Product name mismatch for GTIN {gtin}',
                                'expected': f'GS1 verified: {gs1_product.get("product_name", "N/A")} ({gs1_product.get("brand_name", "N/A")})',
                                'actual': f'Document shows: {item.get("extracted_name", "N/A")}',
                                'gtin': gtin
                            })

                        logger.info(f"GTIN {gtin} verified: {gs1_product.get('product_name', 'N/A')}")
                    else:
                        gtin_verification_item['name_match'] = False
                        gtin_verification_item['match_confidence'] = 0.0
                        enhanced_discrepancies.append({
                            'type': 'GTIN_NOT_VERIFIED',
                            'description': f'GTIN {gtin} could not be verified in GS1 database',
                            'expected': 'Valid GTIN in GS1 registry',
                            'actual': f'GTIN {gtin} not found or invalid',
                            'gtin': gtin
                        })

                        logger.warning(f"GTIN {gtin} not found in GS1 database")

                    gtin_verification.append(gtin_verification_item)

            # Update validation result based on GTIN verification
            original_valid = validation_data.get('validation_result') == 'VALID'
            gtin_issues = len([v for v in gtin_verification if not v.get('name_match', False)])

            # If there are GTIN mismatches, mark as invalid
            if gtin_issues > 0 and original_valid:
                validation_data['validation_result'] = 'INVALID'
                logger.info(f"Validation marked INVALID due to {gtin_issues} GTIN verification issues")

            # Update summary
            summary = validation_data.get('summary', {})
            summary['gtins_verified'] = len([v for v in gtin_verification if v.get('gs1_verified', False)])
            summary['gtins_matched'] = len([v for v in gtin_verification if v.get('name_match', False)])
            summary['gtin_verification_issues'] = gtin_issues

            # Add GTIN verification data
            validation_data['gtin_verification'] = gtin_verification
            validation_data['discrepancies'] = enhanced_discrepancies
            validation_data['summary'] = summary

            logger.info(f"GTIN verification complete: {len(gtin_verification)} GTINs processed")
            return validation_data

        except Exception as e:
            logger.error(f"Error in GTIN verification: {e}")
            # Return original validation data if GTIN verification fails
            return validation_data

    def apply_conservative_missing_item_logic(self, validation_data, order_items):
        """Apply ultra-conservative logic to missing item detection"""
        try:
            logger.info("Applying conservative missing item logic")

            extracted_items = validation_data.get('extracted_items', [])
            discrepancies = list(validation_data.get('discrepancies', []))

            # Remove existing missing item discrepancies to re-evaluate them
            original_missing_discrepancies = []
            filtered_discrepancies = []

            for disc in discrepancies:
                if disc.get('type') == 'MISSING_ITEM':
                    original_missing_discrepancies.append(disc)
                else:
                    filtered_discrepancies.append(disc)

            # Ultra-conservative thresholds
            CONSERVATIVE_MATCH_THRESHOLD = 0.7  # Higher threshold for considering items matched
            MIN_CONFIDENCE_FOR_MISSING = 0.95   # Very high confidence required to mark as missing

            # Build comprehensive matching profile for each order item
            for order_item in order_items:
                order_sku = order_item.get('sku_id', '').lower().strip()
                order_name = order_item.get('name', '').lower().strip()
                order_quantity = order_item.get('quantity', 0)

                logger.info(f"Checking order item: {order_sku} - {order_name} (qty: {order_quantity})")

                # Find potential matches with multiple matching strategies
                potential_matches = []

                for extracted_item in extracted_items:
                    extracted_sku = extracted_item.get('extracted_sku', '').lower().strip()
                    extracted_name = extracted_item.get('extracted_name', '').lower().strip()
                    extracted_gtin = extracted_item.get('extracted_gtin')
                    match_confidence = extracted_item.get('match_confidence', 0)

                    # Strategy 1: Direct SKU match
                    if order_sku and extracted_sku and order_sku == extracted_sku:
                        potential_matches.append({
                            'strategy': 'direct_sku',
                            'confidence': 1.0,
                            'item': extracted_item
                        })
                        logger.info(f"Direct SKU match found: {order_sku}")

                    # Strategy 2: High confidence match from AI
                    elif match_confidence >= CONSERVATIVE_MATCH_THRESHOLD:
                        potential_matches.append({
                            'strategy': 'ai_high_confidence',
                            'confidence': match_confidence,
                            'item': extracted_item
                        })
                        logger.info(f"High confidence AI match: {match_confidence}")

                    # Strategy 3: GTIN verification match
                    if extracted_gtin:
                        gtin_verification = validation_data.get('gtin_verification', [])
                        gtin_info = next((g for g in gtin_verification if g.get('gtin') == extracted_gtin), None)
                        if gtin_info and gtin_info.get('name_match', False):
                            # Cross-check if this GTIN product matches our order item
                            gs1_product = gtin_info.get('gs1_product_info', {})
                            gs1_name = gs1_product.get('product_name', '').lower()

                            # Use bilingual matching for GTIN product name
                            if gs1_name:
                                gtin_name_match, gtin_match_score = self.calculate_bilingual_match(order_name, gs1_product)
                                if gtin_name_match and gtin_match_score >= CONSERVATIVE_MATCH_THRESHOLD:
                                    potential_matches.append({
                                        'strategy': 'gtin_verified',
                                        'confidence': gtin_match_score,
                                        'item': extracted_item,
                                        'gtin': extracted_gtin
                                    })
                                    logger.info(f"GTIN verified match: {extracted_gtin} with score {gtin_match_score}")

                    # Strategy 4: Fuzzy name matching (only as additional confirmation)
                    if order_name and extracted_name:
                        # Create a mock GS1 product structure for bilingual matching
                        mock_product = {
                            'product_names': {'primary': extracted_name, 'english': extracted_name},
                            'brand_names': {'primary': '', 'english': ''}
                        }
                        name_match, name_score = self.calculate_bilingual_match(order_name, mock_product)
                        if name_match and name_score >= CONSERVATIVE_MATCH_THRESHOLD:
                            potential_matches.append({
                                'strategy': 'fuzzy_name',
                                'confidence': name_score,
                                'item': extracted_item
                            })
                            logger.info(f"Fuzzy name match: {order_name} -> {extracted_name} with score {name_score}")

                # Conservative decision making
                best_match = None
                if potential_matches:
                    # Sort by confidence, prioritize direct matches
                    potential_matches.sort(key=lambda x: (x['confidence'], 1 if x['strategy'] == 'direct_sku' else 0), reverse=True)
                    best_match = potential_matches[0]

                    logger.info(f"Best match for {order_sku}: {best_match['strategy']} with confidence {best_match['confidence']}")

                # Ultra-conservative missing item logic
                should_mark_missing = False
                missing_confidence = 0.0

                if not potential_matches:
                    # Only mark as missing if we have very high confidence in extraction completeness
                    extraction_completeness = validation_data.get('confidence_score', 0)
                    overall_match_rate = len([item for item in extracted_items if item.get('match_confidence', 0) >= 0.8])
                    total_extracted = len(extracted_items)

                    if (extraction_completeness >= MIN_CONFIDENCE_FOR_MISSING and
                        total_extracted > 0 and
                        overall_match_rate / total_extracted >= 0.8):  # Most other items matched well

                        # Additional checks for missing item confidence
                        missing_confidence = min(extraction_completeness, 0.98)  # Cap at 98% to stay humble
                        should_mark_missing = True
                        logger.info(f"Conservative missing item detected: {order_sku} with {missing_confidence} confidence")
                    else:
                        logger.info(f"Not confident enough to mark {order_sku} as missing (extraction: {extraction_completeness}, match rate: {overall_match_rate}/{total_extracted})")

                # Add missing item discrepancy only if ultra-conservative criteria are met
                if should_mark_missing:
                    filtered_discrepancies.append({
                        'type': 'MISSING_ITEM',
                        'description': f'Order item not found in GRN with high confidence',
                        'expected': f'{order_item.get("name", "N/A")} (SKU: {order_sku}, Qty: {order_quantity})',
                        'actual': 'Not found in delivery document',
                        'confidence': missing_confidence,
                        'conservative_analysis': True
                    })

            # Update validation data with conservative analysis
            validation_data['discrepancies'] = filtered_discrepancies

            # Update summary
            summary = validation_data.get('summary', {})
            missing_items = len([d for d in filtered_discrepancies if d.get('type') == 'MISSING_ITEM'])
            summary['missing_items_conservative'] = missing_items
            summary['conservative_analysis_applied'] = True

            # Re-evaluate validation result
            if missing_items > 0 and validation_data.get('validation_result') == 'VALID':
                validation_data['validation_result'] = 'INVALID'
                logger.info(f"Validation marked INVALID due to {missing_items} conservatively detected missing items")

            validation_data['summary'] = summary
            logger.info(f"Conservative missing item logic complete: {missing_items} items marked missing")

            return validation_data

        except Exception as e:
            logger.error(f"Error in conservative missing item logic: {e}")
            return validation_data

    def store_validation_result(self, order_id, grn_image_url, validation_result, processing_time_seconds):
        """Store validation result in database"""
        try:
            # Handle both normal validation result and fallback response structures
            validation_data = validation_result.get('validation_data', validation_result)

            # Check if validation result already exists for this order
            existing_validation = ValidationResult.query.filter_by(
                order_id=order_id,
                grn_image_url=grn_image_url
            ).first()

            if existing_validation:
                # Update existing validation
                existing_validation.is_valid = validation_result.get('is_valid', False)
                existing_validation.has_document = validation_data.get('has_document', False)
                existing_validation.confidence_score = validation_result.get('confidence_score', 0)
                existing_validation.extracted_items = json.dumps(validation_data.get('extracted_items', []))
                existing_validation.discrepancies = json.dumps(validation_result.get('discrepancies', []))
                existing_validation.summary = json.dumps(validation_result.get('summary', {}))
                existing_validation.gtin_verification = json.dumps(validation_result.get('gtin_verification', []))
                existing_validation.ai_response = validation_result.get('ai_response', '')
                existing_validation.processing_time = processing_time_seconds
                existing_validation.is_reprocessed = True
                existing_validation.validation_date = datetime.now()

                logger.info(f"Updated existing validation result for order {order_id}")
            else:
                # Create new validation result
                validation_record = ValidationResult(
                    order_id=order_id,
                    grn_image_url=grn_image_url,
                    is_valid=validation_result.get('is_valid', False),
                    has_document=validation_data.get('has_document', False),
                    confidence_score=validation_result.get('confidence_score', 0),
                    extracted_items=json.dumps(validation_data.get('extracted_items', [])),
                    discrepancies=json.dumps(validation_result.get('discrepancies', [])),
                    summary=json.dumps(validation_result.get('summary', {})),
                    gtin_verification=json.dumps(validation_result.get('gtin_verification', [])),
                    ai_response=validation_result.get('ai_response', ''),
                    processing_time=processing_time_seconds
                )

                db.session.add(validation_record)
                logger.info(f"Created new validation result for order {order_id}")

            db.session.commit()
            logger.info(f"Successfully stored validation result for order {order_id} in database")
            return True

        except Exception as e:
            logger.error(f"Error storing validation result for order {order_id}: {e}")
            db.session.rollback()
            return False

    def get_stored_validation_result(self, order_id, grn_image_url=None):
        """Get stored validation result from database"""
        try:
            query = ValidationResult.query.filter_by(order_id=order_id)

            if grn_image_url:
                query = query.filter_by(grn_image_url=grn_image_url)

            # Get the most recent validation for this order
            validation = query.order_by(ValidationResult.validation_date.desc()).first()

            if validation:
                logger.info(f"Found stored validation result for order {order_id}")
                return validation.to_dict()
            else:
                logger.info(f"No stored validation result found for order {order_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting stored validation result: {e}")
            return None

    def validate_grn_against_order(self, order_data, grn_image_url):
        """Validate GRN document against order data using Google AI"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'Google AI API key not configured',
                'is_valid': False
            }

        try:
            validation_start_time = time.time()

            # Download and encode image
            logger.info(f"Downloading GRN image from: {grn_image_url}")
            image_base64, image_format = self.download_image(grn_image_url)
            if not image_base64:
                logger.error(f"Failed to download GRN image from: {grn_image_url}")
                return {
                    'success': False,
                    'error': 'Failed to download GRN image',
                    'is_valid': False
                }

            # Prepare order data for comparison
            order_items = []
            if 'lineItems' in order_data:
                for item in order_data['lineItems']:
                    order_item = {
                        'sku_id': item.get('id', ''),
                        'name': item.get('name', ''),
                        'quantity': item.get('quantity', 0),
                        'unit': item.get('quantityUnit', ''),
                        'weight': item.get('totalWeight', {}).get('value', 0) if item.get('totalWeight') else 0,
                        'weight_unit': item.get('totalWeight', {}).get('unit', '') if item.get('totalWeight') else ''
                    }
                    order_items.append(order_item)

            # Debug logging
            logger.info(f"Prepared {len(order_items)} order items for validation:")
            for item in order_items[:3]:  # Log first 3 items
                logger.info(f"  SKU: {item['sku_id']}, Name: {item['name']}, Qty: {item['quantity']} {item['unit']}")

            # Create enhanced prompt following PRD workflow requirements
            prompt = f"""
You are a professional GRN validation system following a structured workflow. Analyze this image systematically according to the Order Validation Workflow outlined below.

**STEP 1: DOCUMENT DETECTION (Critical First Step)**
Examine the image carefully and determine:
- Does this image contain a readable document (GRN, receipt, invoice, delivery note, etc.)?
- Is the document clear and readable with structured data/text visible?
- If NO document is detected or image is unclear/unreadable, set "has_document": false and "validation_result": "NO_DOCUMENT"

**STEP 2: DATA EXTRACTION (Only if document detected)**
If a document IS present, extract ALL visible items with maximum precision:
- Product names/descriptions (both Arabic and English if present)
- SKU codes/item codes/product IDs
- Quantities with units (boxes, units, kg, etc.)
- **GTIN/BARCODE NUMBERS** (13-digit codes starting with 622, 623, 624 for Egyptian products)
- Package configurations (e.g., 5+1)*4, 2*10, etc.)
- Unit of Measurement details

**STEP 3: ITEM MATCHING LOGIC (Following PRD Priority)**
For each extracted item, attempt matching using this EXACT priority order:
1. **PRIMARY MATCH: SKU** - Match order.sku_id with extracted_sku (exact match)
2. **SECONDARY MATCH: GTIN** - If no SKU match, use extracted_gtin for GS1 lookup
3. **FUZZY NAME MATCHING** - Match product names (Arabic/English bilingual support)

**STEP 4: QUANTITY VALIDATION WITH UOM HANDLING**
Once items are matched, validate quantities considering:
- Unit of Measurement discrepancies (e.g., "12 units" vs "1 box")
- Package configurations (e.g., "6 boxes" vs "6*(5+1) units")
- Weight vs count differences
- Partial deliveries vs full orders

**STEP 5: DISCREPANCY IDENTIFICATION**
Flag ALL discrepancies with specific types:
- MISSING_ITEM: In order but not found in GRN
- EXTRA_ITEM: In GRN but not in order
- QUANTITY_MISMATCH: Different quantities
- GTIN_NAME_MISMATCH: GTIN verified but names don't match
- GTIN_NOT_VERIFIED: GTIN not found in database
- UOM_MISMATCH: Unit of measurement issues

EXPECTED ORDER DATA:
{json.dumps(order_items, indent=2)}

CRITICAL MATCHING INSTRUCTIONS:
- Total Expected Items: {len(order_items)} different SKUs
- MUST match items by SKU first (exact match of sku_id field)
- MUST include full product name and unit of measurement (UOM) data in response
- Look for Egyptian GTIN codes: 13-digit numbers starting with 622, 623, 624
- Common brands: PAPIA, FAMILIA
- Package formats: (5+1)*4, 2*10, etc.
- For each order item above, you MUST attempt to find a matching item in the GRN document
- If you cannot match an item, it should be reported as MISSING_ITEM
- Product names may appear in Arabic in the GRN but are in English in the order data

REQUIRED OUTPUT FORMAT (JSON only):
{{
    "has_document": true or false,
    "document_description": "Brief description of document type found or why no document detected",
    "validation_result": "VALID" or "INVALID" or "NO_DOCUMENT",
    "confidence_score": 0.95,
    "extracted_items": [
        {{
            "extracted_sku": "SKU/item code from document or null",
            "extracted_gtin": "13-digit GTIN/barcode number or null",
            "extracted_name": "product name/description from document",
            "extracted_quantity": "quantity number from document",
            "extracted_unit": "unit of measurement (boxes, units, kg, etc.)",
            "extracted_weight": "weight value if available or null",
            "package_config": "package configuration like (5+1)*4 or null",
            "matched_order_sku": "matching order SKU or null",
            "match_method": "SKU_MATCH or GTIN_MATCH or NAME_MATCH or NONE",
            "match_confidence": 0.98,
            "quantity_equivalent": "calculated equivalent quantity in order units",
            "status": "MATCHED" or "EXTRA" or "QUANTITY_MISMATCH"
        }}
    ],
    "discrepancies": [
        {{
            "type": "MISSING_ITEM" or "EXTRA_ITEM" or "QUANTITY_MISMATCH" or "UOM_MISMATCH" or "GTIN_NAME_MISMATCH" or "GTIN_NOT_VERIFIED",
            "description": "Clear description of the specific issue",
            "expected": "what was expected from order",
            "actual": "what was found in GRN document",
            "sku_id": "relevant SKU if applicable",
            "gtin": "relevant GTIN if applicable",
            "severity": "HIGH" or "MEDIUM" or "LOW"
        }}
    ],
    "summary": {{
        "total_items_expected": {len(order_items)},
        "total_items_found": "number of items found in GRN (integer)",
        "items_perfectly_matched": "items with exact SKU/GTIN/quantity match (integer)",
        "items_with_discrepancies": "items with issues (integer)",
        "gtins_extracted": "number of GTIN codes found (integer)",
        "missing_items": "items in order but not in GRN (integer)",
        "extra_items": "items in GRN but not in order (integer)",
        "quantity_mismatches": "items with quantity differences (integer)"
    }},
    "uom_analysis": {{
        "conversions_attempted": "number of UoM conversions tried",
        "successful_conversions": "conversions that resolved discrepancies",
        "unresolved_uom_issues": "remaining UoM conflicts"
    }}
}}

CRITICAL REQUIREMENTS:
1. **DOCUMENT DETECTION FIRST** - If no readable document: has_document=false, validation_result="NO_DOCUMENT"
2. **FOLLOW PRD MATCHING PRIORITY** - SKU first, then GTIN, then fuzzy name matching
3. **UOM INTELLIGENCE** - Convert between units (boxes↔units, kg↔grams, etc.)
4. **GTIN EXTRACTION** - ALWAYS look for 13-digit barcodes/GTINs starting with 622/623/624 and include in extracted_gtin field
5. **PRECISE QUANTITY MATCHING** - Account for package configurations and include unit details
6. **BILINGUAL SUPPORT** - Handle Arabic/English product names
7. **SEVERITY ASSESSMENT** - Classify discrepancies by business impact
8. **COMPLETE DATA EXTRACTION** - For each item, MUST include sku, gtin, name, quantity, and unit fields
9. **SUMMARY ACCURACY** - Provide exact integer counts in summary section
10. Return ONLY valid JSON, no markdown or extra text
"""

            # Prepare request to Google AI
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": f"image/{image_format}",
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topK": 1,
                    "topP": 0.8,
                    "maxOutputTokens": 4096
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            logger.info(f"Sending request to Google AI API with payload size: {len(str(payload))} chars")

            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=60
            )

            logger.info(f"Google AI API response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"Google AI API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'Google AI API error: {response.status_code} - {response.text[:200]}',
                    'is_valid': False
                }

            # Check if response has content
            if not response.content:
                logger.error("Empty response from Google AI API")
                return {
                    'success': False,
                    'error': 'Empty response from Google AI API',
                    'is_valid': False
                }

            logger.info(f"Google AI API response size: {len(response.content)} bytes")

            try:
                result = response.json()
                logger.info(f"Successfully parsed Google AI API response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode Google AI API response: {e}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response content (first 1000 chars): {response.text[:1000]}")
                return {
                    'success': False,
                    'error': f'Invalid JSON response from Google AI API: {str(e)}',
                    'is_valid': False,
                    'debug_info': {
                        'status_code': response.status_code,
                        'content_type': response.headers.get('content-type', 'unknown'),
                        'content_length': len(response.content)
                    }
                }

            if 'candidates' not in result or not result['candidates']:
                return {
                    'success': False,
                    'error': 'No response from Google AI',
                    'is_valid': False
                }

            # Parse the AI response
            ai_response = result['candidates'][0]['content']['parts'][0]['text']

            # Clean and parse JSON response
            try:
                # Remove any markdown formatting
                ai_response = ai_response.strip()
                if ai_response.startswith('```json'):
                    ai_response = ai_response[7:]
                if ai_response.endswith('```'):
                    ai_response = ai_response[:-3]

                # Clean up common JSON issues
                ai_response = ai_response.strip()

                # Try to fix common JSON issues
                ai_response = self.fix_json_response(ai_response)

                # Clean BOM and other invisible characters
                ai_response = ai_response.encode('utf-8').decode('utf-8-sig').strip()

                # Debug the first and last few characters
                logger.info(f"JSON response starts with: {repr(ai_response[:50])}")
                logger.info(f"JSON response ends with: {repr(ai_response[-50:])}")
                logger.info(f"JSON response length: {len(ai_response)} chars")

                # Check if JSON appears truncated
                if not ai_response.rstrip().endswith('}'):
                    logger.warning("JSON response appears to be truncated (doesn't end with })")

                validation_data = json.loads(ai_response)

                # Enhance validation with GTIN verification from GS1
                enhanced_validation = self.enhance_with_gtin_verification(validation_data)

                # Apply enhanced quantity validation with UoM handling
                uom_enhanced_validation = self.validate_quantities_with_uom(enhanced_validation, order_items)

                # Apply ultra-conservative missing item detection logic
                final_validation = self.apply_conservative_missing_item_logic(uom_enhanced_validation, order_items)

                # Create result object
                result = {
                    'success': True,
                    'is_valid': final_validation.get('validation_result') == 'VALID',
                    'validation_data': final_validation,
                    'confidence_score': final_validation.get('confidence_score', 0),
                    'discrepancies': final_validation.get('discrepancies', []),
                    'summary': final_validation.get('summary', {}),
                    'ai_response': ai_response,
                    'gtin_verification': final_validation.get('gtin_verification', [])
                }

                # Store validation result in database
                order_id = order_data.get('id')
                if order_id:
                    processing_time = time.time() - validation_start_time
                    self.store_validation_result(order_id, grn_image_url, result, processing_time)

                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Error at line {e.lineno}, column {e.colno}, char {e.pos}")
                logger.error(f"AI Response length: {len(ai_response)} chars")
                logger.error(f"AI Response first 200 chars: {repr(ai_response[:200])}")
                logger.error(f"AI Response around error position: {repr(ai_response[max(0, e.pos-50):e.pos+50])}")

                # Try alternative parsing methods
                try:
                    # Try with strict=False to handle Unicode better
                    validation_data = json.loads(ai_response, strict=False)
                    logger.info("Successfully parsed with strict=False")

                    # Continue with normal processing
                    enhanced_validation = self.enhance_with_gtin_verification(validation_data)
                    uom_enhanced_validation = self.validate_quantities_with_uom(enhanced_validation, order_items)
                    final_validation = self.apply_conservative_missing_item_logic(uom_enhanced_validation, order_items)

                    result = {
                        'success': True,
                        'is_valid': final_validation.get('validation_result', 'INVALID') == 'VALID',
                        'has_document': final_validation.get('has_document', False),
                        'confidence_score': final_validation.get('confidence_score', 0.0),
                        'ai_response': json.dumps(final_validation),
                        'extracted_items': final_validation.get('extracted_items', []),
                        'discrepancies': final_validation.get('discrepancies', []),
                        'summary': final_validation.get('summary', {}),
                        'processing_time': time.time() - validation_start_time
                    }

                    # Store validation result in database
                    order_id = order_data.get('id')
                    if order_id:
                        processing_time = time.time() - validation_start_time
                        self.store_validation_result(order_id, grn_image_url, result, processing_time)

                    return result

                except Exception as e2:
                    logger.error(f"Alternative parsing also failed: {e2}")
                    # Try to create a fallback response from partial data
                    fallback_response = self.create_fallback_response(ai_response)
                    if fallback_response:
                        # Store fallback validation result in database
                        order_id = order_data.get('id')
                        if order_id:
                            processing_time = time.time() - validation_start_time
                            self.store_validation_result(order_id, grn_image_url, fallback_response, processing_time)
                        return fallback_response

                return {
                    'success': False,
                    'error': f'Invalid JSON response from AI: {str(e)}',
                    'is_valid': False,
                    'ai_response': ai_response
                }

        except Exception as e:
            logger.error(f"Error validating GRN: {e}")
            return {
                'success': False,
                'error': str(e),
                'is_valid': False
            }
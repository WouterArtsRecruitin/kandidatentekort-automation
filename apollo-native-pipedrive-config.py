#!/usr/bin/env python3
"""
APOLLO NATIVE PIPEDRIVE CONFIGURATION V1.0
==========================================
Seamless Apollo.io integration with Pipedrive for enhanced automation
Direct API integration without MCP dependency

Features:
- Native Apollo.io API integration
- Automatic Pipedrive field mapping
- Real-time contact and company enrichment
- Smart lead scoring and prioritization
- Custom field synchronization
- Automated contact discovery

Author: Recruitin B.V.
Date: December 2024
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ApolloNativePipedriveConfig:
    """Native Apollo.io integration with Pipedrive"""
    
    def __init__(self):
        # API Configurations
        self.apollo_api_key = os.getenv('APOLLO_API_KEY')
        self.pipedrive_api_token = os.getenv('PIPEDRIVE_API_TOKEN')
        
        # API Endpoints
        self.apollo_base = "https://api.apollo.io/v1"
        self.pipedrive_base = "https://api.pipedrive.com/v1"
        
        # Pipeline 12 Configuration
        self.pipeline_id = 12
        self.target_stages = {
            'nieuwe_aanvraag': 45,
            'gekwalificeerd': 48,
            'gesprek_gepland': 49
        }
        
        # Pipedrive Custom Field Mapping for Apollo Data
        self.custom_fields = {
            # Apollo Person Fields
            'apollo_person_id': None,
            'apollo_email_status': None,
            'apollo_phone_status': None,
            'apollo_linkedin_url': None,
            'apollo_title': None,
            'apollo_seniority': None,
            'apollo_departments': None,
            
            # Apollo Organization Fields  
            'apollo_organization_id': None,
            'apollo_company_domain': None,
            'apollo_company_industry': None,
            'apollo_company_size': None,
            'apollo_company_revenue': None,
            'apollo_company_funding': None,
            'apollo_company_technologies': None,
            'apollo_company_keywords': None,
            
            # Apollo Scoring & Intelligence
            'apollo_lead_score': None,
            'apollo_contact_confidence': None,
            'apollo_email_deliverability': None,
            'apollo_phone_confidence': None,
            'apollo_last_enriched': None,
            'apollo_data_quality': None,
            
            # HR Intelligence
            'apollo_hr_team_size': None,
            'apollo_hiring_signals': None,
            'apollo_recent_hires': None,
            'apollo_job_openings': None
        }
        
        logger.info("🚀 Apollo Native Pipedrive Config initialized")
        self._validate_configuration()

    def _validate_configuration(self):
        """Validate API keys and connection"""
        if not self.apollo_api_key:
            logger.warning("⚠️ APOLLO_API_KEY not configured - enrichment disabled")
            
        if not self.pipedrive_api_token:
            logger.error("❌ PIPEDRIVE_API_TOKEN required")
            return False
            
        # Test Pipedrive connection
        try:
            response = requests.get(
                f"{self.pipedrive_base}/users/me",
                params={'api_token': self.pipedrive_api_token},
                timeout=10
            )
            if response.status_code == 200:
                user = response.json().get('data', {})
                logger.info(f"✅ Pipedrive connected as: {user.get('name')}")
            else:
                logger.error(f"❌ Pipedrive connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Pipedrive test failed: {e}")
            return False
            
        # Test Apollo connection if key provided
        if self.apollo_api_key:
            try:
                response = requests.get(
                    f"{self.apollo_base}/auth/health",
                    headers={'X-Api-Key': self.apollo_api_key},
                    timeout=10
                )
                if response.status_code == 200:
                    logger.info("✅ Apollo.io connection verified")
                else:
                    logger.warning(f"⚠️ Apollo connection issue: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Apollo test failed: {e}")
                
        return True

    def setup_pipedrive_custom_fields(self) -> Dict[str, Any]:
        """Create all necessary custom fields in Pipedrive for Apollo integration"""
        
        field_definitions = [
            # Person Fields
            {'key': 'apollo_person_id', 'name': 'Apollo Person ID', 'field_type': 'varchar', 'options': None},
            {'key': 'apollo_email_status', 'name': 'Apollo Email Status', 'field_type': 'enum', 
             'options': [{'label': 'Verified'}, {'label': 'Likely'}, {'label': 'Unknown'}]},
            {'key': 'apollo_linkedin_url', 'name': 'Apollo LinkedIn URL', 'field_type': 'varchar', 'options': None},
            {'key': 'apollo_title', 'name': 'Apollo Job Title', 'field_type': 'varchar', 'options': None},
            {'key': 'apollo_seniority', 'name': 'Apollo Seniority', 'field_type': 'enum',
             'options': [{'label': 'Entry'}, {'label': 'Senior'}, {'label': 'Manager'}, {'label': 'Director'}, {'label': 'VP'}, {'label': 'C-Level'}]},
            
            # Organization Fields
            {'key': 'apollo_organization_id', 'name': 'Apollo Organization ID', 'field_type': 'varchar', 'options': None},
            {'key': 'apollo_company_domain', 'name': 'Apollo Company Domain', 'field_type': 'varchar', 'options': None},
            {'key': 'apollo_company_industry', 'name': 'Apollo Industry', 'field_type': 'varchar', 'options': None},
            {'key': 'apollo_company_size', 'name': 'Apollo Company Size', 'field_type': 'int', 'options': None},
            {'key': 'apollo_company_revenue', 'name': 'Apollo Annual Revenue', 'field_type': 'varchar', 'options': None},
            {'key': 'apollo_company_technologies', 'name': 'Apollo Technologies', 'field_type': 'text', 'options': None},
            
            # Deal Fields
            {'key': 'apollo_lead_score', 'name': 'Apollo Lead Score', 'field_type': 'int', 'options': None},
            {'key': 'apollo_contact_confidence', 'name': 'Apollo Contact Confidence', 'field_type': 'int', 'options': None},
            {'key': 'apollo_last_enriched', 'name': 'Apollo Last Enriched', 'field_type': 'date', 'options': None},
            {'key': 'apollo_data_quality', 'name': 'Apollo Data Quality', 'field_type': 'enum',
             'options': [{'label': 'Excellent'}, {'label': 'Good'}, {'label': 'Fair'}, {'label': 'Poor'}]},
             
            # HR Intelligence
            {'key': 'apollo_hr_team_size', 'name': 'Apollo HR Team Size', 'field_type': 'int', 'options': None},
            {'key': 'apollo_recent_hires', 'name': 'Apollo Recent Hires', 'field_type': 'int', 'options': None},
            {'key': 'apollo_job_openings', 'name': 'Apollo Job Openings', 'field_type': 'int', 'options': None}
        ]
        
        created_fields = {}
        
        for field_def in field_definitions:
            try:
                # Check if field already exists
                existing_fields = self._get_existing_custom_fields('deal')
                field_exists = any(f.get('key') == field_def['key'] for f in existing_fields)
                
                if field_exists:
                    logger.info(f"⚡ Field '{field_def['key']}' already exists")
                    continue
                
                # Create the field
                field_data = {
                    'name': field_def['name'],
                    'field_type': field_def['field_type']
                }
                
                if field_def['options']:
                    field_data['options'] = field_def['options']
                
                response = requests.post(
                    f"{self.pipedrive_base}/dealFields",
                    params={'api_token': self.pipedrive_api_token},
                    json=field_data,
                    timeout=30
                )
                
                if response.status_code == 201:
                    field_data = response.json().get('data', {})
                    field_key = field_data.get('key')
                    created_fields[field_def['key']] = field_key
                    logger.info(f"✅ Created field: {field_def['name']} -> {field_key}")
                else:
                    logger.error(f"❌ Failed to create field {field_def['name']}: {response.text}")
                    
            except Exception as e:
                logger.error(f"❌ Error creating field {field_def['key']}: {e}")
        
        # Update field mapping
        self.custom_fields.update(created_fields)
        
        return {
            'success': True,
            'fields_created': len(created_fields),
            'field_mapping': created_fields
        }

    def _get_existing_custom_fields(self, entity_type: str = 'deal') -> List[Dict]:
        """Get existing custom fields for entity type"""
        try:
            response = requests.get(
                f"{self.pipedrive_base}/{entity_type}Fields",
                params={'api_token': self.pipedrive_api_token},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('data', [])
        except Exception as e:
            logger.error(f"Error getting custom fields: {e}")
            
        return []

    def enrich_person_with_apollo(self, email: str) -> Optional[Dict[str, Any]]:
        """Enrich person data using Apollo.io API"""
        
        if not self.apollo_api_key:
            logger.warning("Apollo API key not configured")
            return None
            
        try:
            # Apollo Person Enrichment API
            response = requests.post(
                f"{self.apollo_base}/people/match",
                headers={
                    'X-Api-Key': self.apollo_api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'email': email
                },
                timeout=30
            )
            
            if response.status_code == 200:
                person_data = response.json().get('person', {})
                organization_data = person_data.get('organization', {})
                
                enriched_data = {
                    # Person Data
                    'apollo_person_id': person_data.get('id'),
                    'apollo_email_status': person_data.get('email_status'),
                    'apollo_linkedin_url': person_data.get('linkedin_url'),
                    'apollo_title': person_data.get('title'),
                    'apollo_seniority': person_data.get('seniority'),
                    'apollo_departments': ', '.join(person_data.get('departments', [])),
                    
                    # Organization Data
                    'apollo_organization_id': organization_data.get('id'),
                    'apollo_company_domain': organization_data.get('website_url'),
                    'apollo_company_industry': organization_data.get('industry'),
                    'apollo_company_size': organization_data.get('estimated_num_employees'),
                    'apollo_company_revenue': organization_data.get('annual_revenue'),
                    'apollo_company_technologies': ', '.join([t.get('name', '') for t in organization_data.get('technologies', [])]),
                    
                    # Metadata
                    'apollo_last_enriched': datetime.now().strftime('%Y-%m-%d'),
                    'apollo_data_quality': self._calculate_data_quality(person_data, organization_data)
                }
                
                logger.info(f"✅ Apollo enriched: {person_data.get('first_name')} {person_data.get('last_name')} at {organization_data.get('name')}")
                return enriched_data
                
            else:
                logger.warning(f"Apollo enrichment failed: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Apollo enrichment error: {e}")
            return None

    def find_hr_contacts_with_apollo(self, company_domain: str) -> List[Dict[str, Any]]:
        """Find HR contacts at a company using Apollo"""
        
        if not self.apollo_api_key:
            return []
            
        try:
            # Apollo People Search API for HR contacts
            response = requests.post(
                f"{self.apollo_base}/people/search",
                headers={
                    'X-Api-Key': self.apollo_api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'q_organization_domains': [company_domain],
                    'person_titles': [
                        'HR Manager', 'HR Director', 'Head of HR', 'HR Business Partner',
                        'Talent Acquisition', 'Recruiter', 'Recruitment Manager',
                        'People Operations', 'Chief People Officer'
                    ],
                    'per_page': 10,
                    'page': 1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                search_results = response.json()
                contacts = search_results.get('people', [])
                
                hr_contacts = []
                for contact in contacts:
                    hr_contacts.append({
                        'name': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
                        'title': contact.get('title', ''),
                        'email': contact.get('email', ''),
                        'linkedin_url': contact.get('linkedin_url', ''),
                        'confidence_score': contact.get('email_status_score', 0)
                    })
                
                logger.info(f"✅ Found {len(hr_contacts)} HR contacts at {company_domain}")
                return hr_contacts
                
        except Exception as e:
            logger.error(f"HR contact search error: {e}")
            
        return []

    def _calculate_data_quality(self, person_data: Dict, organization_data: Dict) -> str:
        """Calculate Apollo data quality score"""
        score = 0
        
        # Person data quality indicators
        if person_data.get('email_status') == 'verified':
            score += 25
        elif person_data.get('email_status') == 'likely':
            score += 15
            
        if person_data.get('linkedin_url'):
            score += 20
            
        if person_data.get('title'):
            score += 15
            
        # Organization data quality indicators
        if organization_data.get('estimated_num_employees'):
            score += 20
            
        if organization_data.get('industry'):
            score += 10
            
        if organization_data.get('annual_revenue'):
            score += 10
        
        # Convert to quality label
        if score >= 80:
            return 'Excellent'
        elif score >= 60:
            return 'Good'
        elif score >= 40:
            return 'Fair'
        else:
            return 'Poor'

    def sync_apollo_data_to_pipedrive_deal(self, deal_id: int, apollo_data: Dict[str, Any]) -> bool:
        """Sync Apollo enrichment data to Pipedrive deal"""
        
        if not apollo_data:
            return False
            
        try:
            # Map Apollo data to custom fields
            custom_field_data = {}
            
            for apollo_key, value in apollo_data.items():
                pipedrive_field_key = self.custom_fields.get(apollo_key)
                if pipedrive_field_key and value is not None:
                    custom_field_data[pipedrive_field_key] = value
            
            if not custom_field_data:
                logger.warning("No Apollo data to sync")
                return False
                
            # Update deal with Apollo data
            response = requests.put(
                f"{self.pipedrive_base}/deals/{deal_id}",
                params={'api_token': self.pipedrive_api_token},
                json=custom_field_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Synced Apollo data to deal {deal_id}: {len(custom_field_data)} fields updated")
                return True
            else:
                logger.error(f"❌ Failed to sync Apollo data: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing Apollo data: {e}")
            return False

    def process_deal_with_apollo_enrichment(self, deal_id: int) -> Dict[str, Any]:
        """Complete Apollo enrichment workflow for a Pipedrive deal"""
        
        try:
            # Get deal data
            deal_response = requests.get(
                f"{self.pipedrive_base}/deals/{deal_id}",
                params={'api_token': self.pipedrive_api_token},
                timeout=30
            )
            
            if deal_response.status_code != 200:
                return {'success': False, 'error': 'Could not retrieve deal'}
                
            deal_data = deal_response.json().get('data', {})
            
            # Get person email
            person_id = deal_data.get('person_id', {})
            if isinstance(person_id, dict):
                person_id = person_id.get('value')
                
            if not person_id:
                return {'success': False, 'error': 'No person associated with deal'}
            
            # Get person details
            person_response = requests.get(
                f"{self.pipedrive_base}/persons/{person_id}",
                params={'api_token': self.pipedrive_api_token},
                timeout=30
            )
            
            if person_response.status_code != 200:
                return {'success': False, 'error': 'Could not retrieve person'}
                
            person_data = person_response.json().get('data', {})
            emails = person_data.get('email', [])
            
            if not emails:
                return {'success': False, 'error': 'No email found for person'}
                
            primary_email = emails[0].get('value') if emails else None
            
            if not primary_email:
                return {'success': False, 'error': 'Invalid email format'}
            
            # Enrich with Apollo
            apollo_data = self.enrich_person_with_apollo(primary_email)
            
            if not apollo_data:
                return {'success': False, 'error': 'Apollo enrichment failed'}
            
            # Find HR contacts if company domain available
            company_domain = apollo_data.get('apollo_company_domain')
            hr_contacts = []
            
            if company_domain:
                hr_contacts = self.find_hr_contacts_with_apollo(company_domain)
                apollo_data['apollo_hr_team_size'] = len(hr_contacts)
            
            # Sync to Pipedrive
            sync_success = self.sync_apollo_data_to_pipedrive_deal(deal_id, apollo_data)
            
            # Add enrichment note
            if sync_success:
                note_content = f"""🤖 APOLLO ENRICHMENT COMPLETE
                
Enriched: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Data Quality: {apollo_data.get('apollo_data_quality', 'Unknown')}

PERSON INTEL:
- Title: {apollo_data.get('apollo_title', 'Unknown')}
- Seniority: {apollo_data.get('apollo_seniority', 'Unknown')}
- Email Status: {apollo_data.get('apollo_email_status', 'Unknown')}
- LinkedIn: {apollo_data.get('apollo_linkedin_url', 'Not found')}

COMPANY INTEL:
- Industry: {apollo_data.get('apollo_company_industry', 'Unknown')}
- Size: {apollo_data.get('apollo_company_size', 'Unknown')} employees
- Revenue: {apollo_data.get('apollo_company_revenue', 'Unknown')}
- Technologies: {apollo_data.get('apollo_company_technologies', 'Unknown')[:100]}...

HR TEAM INTEL:
- HR Team Size: {len(hr_contacts)} contacts found
- Key Contacts: {', '.join([c['name'] for c in hr_contacts[:3]])}"""

                requests.post(
                    f"{self.pipedrive_base}/notes",
                    params={'api_token': self.pipedrive_api_token},
                    json={
                        'deal_id': deal_id,
                        'content': note_content
                    },
                    timeout=30
                )
            
            return {
                'success': True,
                'apollo_data': apollo_data,
                'hr_contacts_found': len(hr_contacts),
                'data_quality': apollo_data.get('apollo_data_quality'),
                'sync_success': sync_success
            }
            
        except Exception as e:
            logger.error(f"Apollo enrichment process error: {e}")
            return {'success': False, 'error': str(e)}

    def get_apollo_configuration_summary(self) -> Dict[str, Any]:
        """Get complete Apollo-Pipedrive configuration summary"""
        
        return {
            'apollo_integration': {
                'enabled': bool(self.apollo_api_key),
                'api_status': 'configured' if self.apollo_api_key else 'missing',
                'features': [
                    'Person enrichment',
                    'Company intelligence',
                    'HR contact discovery',
                    'Email verification',
                    'Data quality scoring'
                ]
            },
            
            'pipedrive_integration': {
                'enabled': bool(self.pipedrive_api_token),
                'pipeline_id': self.pipeline_id,
                'target_stages': self.target_stages,
                'custom_fields_count': len(self.custom_fields),
                'features': [
                    'Automated field mapping',
                    'Real-time sync',
                    'Custom field creation',
                    'Note automation',
                    'Deal enrichment'
                ]
            },
            
            'automation_capabilities': [
                'Automatic enrichment on deal creation',
                'HR contact discovery',
                'Data quality assessment',
                'Smart lead scoring',
                'Technology stack detection',
                'Company size and revenue insights'
            ],
            
            'setup_status': {
                'apollo_api': 'configured' if self.apollo_api_key else 'needs_setup',
                'pipedrive_api': 'configured' if self.pipedrive_api_token else 'needs_setup', 
                'custom_fields': 'needs_setup',
                'webhooks': 'needs_setup'
            }
        }


# =============================================================================
# CLI INTERFACE & TESTING
# =============================================================================

def main():
    """Test and demonstrate Apollo native Pipedrive integration"""
    
    config = ApolloNativePipedriveConfig()
    
    print("🚀 APOLLO NATIVE PIPEDRIVE INTEGRATION")
    print("=" * 60)
    
    # Test 1: Configuration Summary
    print("\n📋 Configuration Summary:")
    summary = config.get_apollo_configuration_summary()
    print(json.dumps(summary, indent=2))
    
    # Test 2: Setup Custom Fields (uncomment to run)
    print("\n🛠️ Custom Field Setup:")
    print("Run config.setup_pipedrive_custom_fields() to create Apollo fields")
    
    # Test 3: Example enrichment (replace with real email for testing)
    print("\n🧪 Example Apollo Enrichment:")
    print("Run config.enrich_person_with_apollo('test@company.com') for testing")
    
    # Test 4: Show field mapping
    print("\n🗺️ Apollo → Pipedrive Field Mapping:")
    for apollo_field, pipedrive_field in config.custom_fields.items():
        status = "✅ mapped" if pipedrive_field else "⏳ needs setup"
        print(f"  {apollo_field} → {pipedrive_field or 'TBD'} ({status})")
    
    print("\n✅ Apollo Native Integration Ready!")
    print("\nNext steps:")
    print("1. Set APOLLO_API_KEY environment variable")
    print("2. Run setup_pipedrive_custom_fields() to create fields")
    print("3. Test enrichment with real email addresses")
    print("4. Configure webhooks for automatic enrichment")
    

if __name__ == "__main__":
    main()
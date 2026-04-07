#!/usr/bin/env python3
"""
PIPEDRIVE PIPELINE 12 - ENHANCED TASK AUTOMATION V2.0
====================================================
Advanced task creation and management for Vacature Analyse pipeline
Focus: Smart task routing, automated follow-ups, priority-based scheduling

Features:
- Intelligent task creation based on deal stage transitions
- Apollo-enhanced task prioritization 
- Smart task templates for different scenarios
- Automated task scheduling and reminders
- Task completion triggers for next actions
- Pipeline 12 optimization with native Pipedrive configuration

Author: Recruitin B.V.
Date: December 2024
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipedriveTaskAutomation:
    """Enhanced Pipedrive task automation for Pipeline 12 Vacature Analyse"""
    
    def __init__(self):
        self.api_token = os.getenv('PIPEDRIVE_API_TOKEN')
        self.base_url = "https://api.pipedrive.com/v1"
        
        # Pipeline 12 Configuration
        self.pipeline_id = 12  # Vacature Analyse Pipeline
        self.stages = {
            'nieuwe_aanvraag': 45,     # New request
            'in_analyse': 46,          # Analysis in progress
            'analyse_compleet': 47,    # Analysis complete
            'gekwalificeerd': 48,      # Qualified lead
            'gesprek_gepland': 49,     # Meeting scheduled
            'voorstel_verstuurd': 50,  # Proposal sent
            'gesloten_gewonnen': 51,   # Won
            'gesloten_verloren': 52    # Lost
        }
        
        # Task Templates based on deal scenarios
        self.task_templates = self._load_task_templates()
        
        # Apollo integration for enhanced task prioritization
        self.apollo_enabled = os.getenv('ANTHROPIC_API_KEY') is not None
        
        logger.info("🚀 Pipedrive Task Automation V2.0 initialized for Pipeline 12")

    def _load_task_templates(self) -> Dict[str, List[Dict]]:
        """Load intelligent task templates for different scenarios"""
        return {
            'high_priority_lead': [
                {
                    'subject': '🔥 HOT LEAD: Direct contact within 2 hours',
                    'type': 'call',
                    'due_hours': 2,
                    'note': 'High-value lead (score 85+). Priority contact required. Review Apollo insights before calling.',
                    'assignee': 'auto'  # Auto-assign to deal owner
                },
                {
                    'subject': '📊 Prepare personalized proposal based on analysis',
                    'type': 'task',
                    'due_hours': 24,
                    'note': 'Create tailored proposal using vacancy analysis results. Include before/after examples.',
                    'assignee': 'auto'
                }
            ],
            
            'medium_priority_lead': [
                {
                    'subject': '📞 Follow-up call within 48 hours',
                    'type': 'call', 
                    'due_hours': 48,
                    'note': 'Quality lead. Schedule call to discuss analysis results and next steps.',
                    'assignee': 'auto'
                },
                {
                    'subject': '📧 Send personalized follow-up email',
                    'type': 'email',
                    'due_hours': 72,
                    'note': 'Send custom email with specific insights from vacancy analysis.',
                    'assignee': 'auto'
                }
            ],
            
            'analysis_complete': [
                {
                    'subject': '✅ Analysis delivered - Schedule follow-up in 3 days',
                    'type': 'call',
                    'due_hours': 72,
                    'note': 'Check if client received analysis and discuss implementation. Ask for feedback.',
                    'assignee': 'auto'
                },
                {
                    'subject': '📈 Track vacancy results after 1 week',
                    'type': 'task',
                    'due_hours': 168,  # 1 week
                    'note': 'Follow up on vacancy performance. Ask about application rates and candidate quality.',
                    'assignee': 'auto'
                }
            ],
            
            'qualified_lead': [
                {
                    'subject': '📅 Schedule discovery call',
                    'type': 'call',
                    'due_hours': 24,
                    'note': 'Schedule 30-minute discovery call to discuss broader recruitment challenges.',
                    'assignee': 'auto'
                },
                {
                    'subject': '🎯 Prepare meeting agenda with Apollo insights',
                    'type': 'task',
                    'due_hours': 2,  # Before the call
                    'note': 'Review Apollo company data, prepare targeted questions about recruitment challenges.',
                    'assignee': 'auto'
                }
            ],
            
            'meeting_scheduled': [
                {
                    'subject': '📋 Pre-meeting preparation',
                    'type': 'task',
                    'due_hours': 2,  # 2 hours before
                    'note': 'Review client background, prepare materials, test video call setup.',
                    'assignee': 'auto'
                },
                {
                    'subject': '📝 Send meeting confirmation and agenda',
                    'type': 'email',
                    'due_hours': 24,
                    'note': 'Confirm meeting time, send agenda, include relevant analysis materials.',
                    'assignee': 'auto'
                }
            ],
            
            'proposal_sent': [
                {
                    'subject': '📞 Follow-up call 3 days after proposal',
                    'type': 'call',
                    'due_hours': 72,
                    'note': 'Check if proposal was received, answer questions, discuss next steps.',
                    'assignee': 'auto'
                },
                {
                    'subject': '📊 Send additional case studies if needed',
                    'type': 'task',
                    'due_hours': 120,  # 5 days
                    'note': 'If client hesitant, send relevant case studies and success stories.',
                    'assignee': 'auto'
                }
            ],
            
            'nurture_sequence': [
                {
                    'subject': '💡 Send recruitment tip #1: Function title optimization',
                    'type': 'email',
                    'due_hours': 168,  # 1 week
                    'note': 'Send valuable tip about function titles. Build trust and expertise.',
                    'assignee': 'auto'
                },
                {
                    'subject': '📈 Check in on vacancy performance',
                    'type': 'call',
                    'due_hours': 336,  # 2 weeks
                    'note': 'Personal check-in. How are results? Any other vacancies we can help with?',
                    'assignee': 'auto'
                }
            ]
        }

    def calculate_task_priority(self, deal_data: Dict, apollo_score: Optional[int] = None) -> str:
        """Calculate task priority based on deal and Apollo data"""
        priority = 'normal'
        
        # Apollo-based prioritization
        if apollo_score:
            if apollo_score >= 85:
                priority = 'high'
            elif apollo_score >= 70:
                priority = 'normal'
            else:
                priority = 'low'
        
        # Deal value based prioritization
        deal_value = deal_data.get('value', 0)
        if deal_value >= 25000:
            priority = 'high'
        elif deal_value >= 15000 and priority != 'high':
            priority = 'normal'
            
        # Custom field based prioritization
        custom_fields = deal_data.get('custom_fields', {})
        if custom_fields.get('immediate_callback_needed'):
            priority = 'high'
            
        return priority

    def get_apollo_insights(self, deal_id: int) -> Dict[str, Any]:
        """Extract Apollo insights from deal notes and custom fields"""
        insights = {
            'lead_score': 0,
            'company_size': 'unknown',
            'industry': 'unknown',
            'hr_contacts': 0,
            'decision_makers': 0,
            'enhanced': False
        }
        
        try:
            # Get deal details including custom fields
            response = requests.get(
                f"{self.base_url}/deals/{deal_id}",
                params={'api_token': self.api_token},
                timeout=30
            )
            
            if response.status_code == 200:
                deal_data = response.json().get('data', {})
                
                # Extract Apollo data from custom fields (if they exist)
                # These would be set during deal creation with Apollo integration
                insights['lead_score'] = deal_data.get('apollo_lead_score', 0)
                insights['company_size'] = deal_data.get('apollo_company_employees', 'unknown')
                insights['industry'] = deal_data.get('apollo_company_industry', 'unknown')
                insights['hr_contacts'] = deal_data.get('apollo_hr_contacts_found', 0)
                insights['decision_makers'] = deal_data.get('apollo_decision_makers_found', 0)
                insights['enhanced'] = deal_data.get('apollo_enhanced', False)
                
        except Exception as e:
            logger.error(f"Error getting Apollo insights: {e}")
            
        return insights

    def create_task(self, 
                   subject: str,
                   deal_id: int,
                   assignee_id: int,
                   due_datetime: datetime,
                   task_type: str = 'task',
                   note: str = '',
                   priority: str = 'normal') -> Optional[int]:
        """Create a single task in Pipedrive"""
        
        if not self.api_token:
            logger.error("No Pipedrive API token configured")
            return None
            
        try:
            task_data = {
                'subject': subject,
                'deal_id': deal_id,
                'user_id': assignee_id,
                'due_date': due_datetime.strftime('%Y-%m-%d'),
                'due_time': due_datetime.strftime('%H:%M'),
                'type': task_type,
                'note': note,
                'done': 0
            }
            
            response = requests.post(
                f"{self.base_url}/activities",
                params={'api_token': self.api_token},
                json=task_data,
                timeout=30
            )
            
            if response.status_code == 201:
                task_id = response.json().get('data', {}).get('id')
                logger.info(f"✅ Created task: {subject[:50]}... (ID: {task_id})")
                return task_id
            else:
                logger.error(f"Failed to create task: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def create_task_sequence(self, 
                           template_key: str,
                           deal_id: int,
                           assignee_id: int,
                           apollo_insights: Dict = None) -> List[int]:
        """Create a sequence of tasks based on template"""
        
        if template_key not in self.task_templates:
            logger.error(f"Unknown template: {template_key}")
            return []
            
        tasks = self.task_templates[template_key]
        created_task_ids = []
        base_time = datetime.now()
        
        for task_template in tasks:
            # Calculate due time
            due_hours = task_template.get('due_hours', 24)
            due_datetime = base_time + timedelta(hours=due_hours)
            
            # Enhance note with Apollo insights
            note = task_template.get('note', '')
            if apollo_insights and apollo_insights.get('enhanced'):
                note += f"\n\n🤖 Apollo Insights:\n"
                note += f"- Lead Score: {apollo_insights.get('lead_score', 0)}/100\n"
                note += f"- Company Size: {apollo_insights.get('company_size', 'unknown')}\n"
                note += f"- Industry: {apollo_insights.get('industry', 'unknown')}\n"
                note += f"- HR Contacts Found: {apollo_insights.get('hr_contacts', 0)}\n"
                note += f"- Decision Makers: {apollo_insights.get('decision_makers', 0)}"
            
            # Create the task
            task_id = self.create_task(
                subject=task_template['subject'],
                deal_id=deal_id,
                assignee_id=assignee_id,
                due_datetime=due_datetime,
                task_type=task_template.get('type', 'task'),
                note=note
            )
            
            if task_id:
                created_task_ids.append(task_id)
                
        logger.info(f"✅ Created {len(created_task_ids)} tasks for template '{template_key}'")
        return created_task_ids

    def handle_stage_transition(self, deal_id: int, old_stage_id: int, new_stage_id: int) -> Dict[str, Any]:
        """Handle automated task creation on stage transitions"""
        
        try:
            # Get deal data
            deal_response = requests.get(
                f"{self.base_url}/deals/{deal_id}",
                params={'api_token': self.api_token},
                timeout=30
            )
            
            if deal_response.status_code != 200:
                return {'success': False, 'error': 'Could not retrieve deal data'}
                
            deal_data = deal_response.json().get('data', {})
            assignee_id = deal_data.get('user_id', {}).get('id')
            
            if not assignee_id:
                return {'success': False, 'error': 'No assignee found for deal'}
            
            # Get Apollo insights
            apollo_insights = self.get_apollo_insights(deal_id)
            
            # Determine which tasks to create based on new stage
            template_key = None
            lead_score = apollo_insights.get('lead_score', 0)
            
            if new_stage_id == self.stages['nieuwe_aanvraag']:
                # New request - determine priority
                if lead_score >= 85:
                    template_key = 'high_priority_lead'
                elif lead_score >= 60:
                    template_key = 'medium_priority_lead'
                else:
                    template_key = 'nurture_sequence'
                    
            elif new_stage_id == self.stages['analyse_compleet']:
                template_key = 'analysis_complete'
                
            elif new_stage_id == self.stages['gekwalificeerd']:
                template_key = 'qualified_lead'
                
            elif new_stage_id == self.stages['gesprek_gepland']:
                template_key = 'meeting_scheduled'
                
            elif new_stage_id == self.stages['voorstel_verstuurd']:
                template_key = 'proposal_sent'
            
            # Create task sequence if template found
            created_tasks = []
            if template_key:
                created_tasks = self.create_task_sequence(
                    template_key=template_key,
                    deal_id=deal_id,
                    assignee_id=assignee_id,
                    apollo_insights=apollo_insights
                )
            
            # Add note to deal about automated tasks
            if created_tasks:
                note_content = f"""🤖 AUTOMATED TASK SEQUENCE CREATED
                
Stage Transition: {old_stage_id} → {new_stage_id}
Template Used: {template_key}
Tasks Created: {len(created_tasks)}
Apollo Enhanced: {'✅' if apollo_insights.get('enhanced') else '❌'}
Lead Score: {apollo_insights.get('lead_score', 0)}/100

Task IDs: {', '.join(map(str, created_tasks))}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""

                requests.post(
                    f"{self.base_url}/notes",
                    params={'api_token': self.api_token},
                    json={
                        'deal_id': deal_id,
                        'content': note_content
                    },
                    timeout=30
                )
            
            return {
                'success': True,
                'template_used': template_key,
                'tasks_created': len(created_tasks),
                'task_ids': created_tasks,
                'apollo_insights': apollo_insights
            }
            
        except Exception as e:
            logger.error(f"Error handling stage transition: {e}")
            return {'success': False, 'error': str(e)}

    def create_custom_task_for_deal(self, 
                                  deal_id: int, 
                                  task_subject: str,
                                  due_hours: int = 24,
                                  task_type: str = 'task',
                                  custom_note: str = '') -> Optional[int]:
        """Create a custom task for a specific deal"""
        
        try:
            # Get deal and assignee info
            deal_response = requests.get(
                f"{self.base_url}/deals/{deal_id}",
                params={'api_token': self.api_token},
                timeout=30
            )
            
            if deal_response.status_code != 200:
                return None
                
            deal_data = deal_response.json().get('data', {})
            assignee_id = deal_data.get('user_id', {}).get('id')
            
            if not assignee_id:
                return None
            
            # Calculate due time
            due_datetime = datetime.now() + timedelta(hours=due_hours)
            
            # Get Apollo insights for enhanced note
            apollo_insights = self.get_apollo_insights(deal_id)
            note = custom_note
            
            if apollo_insights.get('enhanced'):
                note += f"\n\n🤖 Context (Apollo):\n"
                note += f"Lead Score: {apollo_insights.get('lead_score')}/100, "
                note += f"Company: {apollo_insights.get('company_size')} employees in {apollo_insights.get('industry')}"
            
            return self.create_task(
                subject=task_subject,
                deal_id=deal_id,
                assignee_id=assignee_id,
                due_datetime=due_datetime,
                task_type=task_type,
                note=note
            )
            
        except Exception as e:
            logger.error(f"Error creating custom task: {e}")
            return None

    def bulk_create_missing_tasks(self) -> Dict[str, Any]:
        """Audit Pipeline 12 and create missing tasks for existing deals"""
        
        try:
            # Get all open deals in Pipeline 12
            response = requests.get(
                f"{self.base_url}/deals",
                params={
                    'api_token': self.api_token,
                    'pipeline_id': self.pipeline_id,
                    'status': 'open',
                    'limit': 500
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {'success': False, 'error': 'Could not retrieve deals'}
            
            deals = response.json().get('data', []) or []
            processed = 0
            tasks_created = 0
            
            for deal in deals:
                deal_id = deal.get('id')
                stage_id = deal.get('stage_id')
                
                # Check if deal has any recent tasks
                tasks_response = requests.get(
                    f"{self.base_url}/deals/{deal_id}/activities",
                    params={
                        'api_token': self.api_token,
                        'type': 'task'
                    },
                    timeout=30
                )
                
                existing_tasks = []
                if tasks_response.status_code == 200:
                    existing_tasks = tasks_response.json().get('data', []) or []
                
                # Create tasks if none exist or very few
                if len(existing_tasks) < 2:  # Threshold: less than 2 tasks
                    result = self.handle_stage_transition(deal_id, stage_id, stage_id)
                    if result.get('success'):
                        tasks_created += result.get('tasks_created', 0)
                
                processed += 1
                
                # Rate limiting
                if processed % 10 == 0:
                    import time
                    time.sleep(1)
            
            logger.info(f"✅ Bulk task creation complete: {processed} deals processed, {tasks_created} tasks created")
            
            return {
                'success': True,
                'deals_processed': processed,
                'tasks_created': tasks_created
            }
            
        except Exception as e:
            logger.error(f"Error in bulk task creation: {e}")
            return {'success': False, 'error': str(e)}

    def setup_pipeline_12_automation(self) -> Dict[str, Any]:
        """Setup Pipeline 12 with optimal configuration for automation"""
        
        automation_config = {
            'pipeline_id': self.pipeline_id,
            'stages': self.stages,
            'task_automation': {
                'enabled': True,
                'templates': list(self.task_templates.keys()),
                'apollo_integration': self.apollo_enabled
            },
            'recommended_webhooks': [
                {
                    'event': 'deal.stage_changed',
                    'target_pipeline': self.pipeline_id,
                    'action': 'create_stage_tasks'
                },
                {
                    'event': 'deal.created', 
                    'target_pipeline': self.pipeline_id,
                    'action': 'create_initial_tasks'
                }
            ],
            'custom_fields_needed': [
                'apollo_lead_score',
                'apollo_company_employees',
                'apollo_company_industry', 
                'apollo_hr_contacts_found',
                'apollo_decision_makers_found',
                'apollo_enhanced',
                'task_automation_enabled'
            ]
        }
        
        logger.info("📋 Pipeline 12 automation configuration ready")
        return automation_config


# =============================================================================
# CLI INTERFACE & TESTING
# =============================================================================

def main():
    """Test and demonstrate the enhanced task automation"""
    
    automation = PipedriveTaskAutomation()
    
    # Test 1: Create tasks for high priority lead
    print("🧪 TEST 1: High Priority Lead Task Creation")
    print("=" * 50)
    
    # Simulate Apollo insights for testing
    mock_apollo_insights = {
        'lead_score': 87,
        'company_size': 250,
        'industry': 'Technology',
        'hr_contacts': 3,
        'decision_makers': 2,
        'enhanced': True
    }
    
    # This would typically be called by a webhook
    # test_deal_id = 12345  # Replace with real deal ID for testing
    # tasks = automation.create_task_sequence(
    #     'high_priority_lead', 
    #     test_deal_id, 
    #     12345,  # assignee_id
    #     mock_apollo_insights
    # )
    # print(f"Created {len(tasks)} tasks for high priority lead")
    
    # Test 2: Show configuration
    print("\n🔧 TEST 2: Pipeline 12 Configuration")
    print("=" * 50)
    config = automation.setup_pipeline_12_automation()
    print(json.dumps(config, indent=2))
    
    # Test 3: Show available templates
    print("\n📋 TEST 3: Available Task Templates")
    print("=" * 50)
    for template_name, tasks in automation.task_templates.items():
        print(f"\n{template_name.upper()}:")
        for i, task in enumerate(tasks, 1):
            print(f"  {i}. {task['subject']} ({task['type']}, {task['due_hours']}h)")
    
    print("\n✅ Task Automation System Ready!")
    print("\nNext steps:")
    print("1. Set PIPEDRIVE_API_TOKEN environment variable")
    print("2. Configure webhooks for deal stage changes")
    print("3. Set up Apollo integration custom fields")
    print("4. Test with real deals in Pipeline 12")


if __name__ == "__main__":
    main()
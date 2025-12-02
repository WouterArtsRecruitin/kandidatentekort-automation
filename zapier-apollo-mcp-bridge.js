/**
 * 🔗 ZAPIER-APOLLO MCP BRIDGE
 * ===========================
 * Complete workflow automation bridge tussen Zapier en Apollo MCP server
 * 
 * Features:
 * - Direct Apollo MCP tool calls vanuit Zapier
 * - Enhanced Typeform → Apollo → Pipedrive workflow  
 * - Error handling & retry logic
 * - Performance monitoring & analytics
 * 
 * Author: Recruitin B.V.
 * Date: December 2024
 */

// =============================================================================
// APOLLO MCP CLIENT FOR ZAPIER
// =============================================================================

class ZapierApolloMCPClient {
    constructor(mcpEndpoint = 'http://localhost:3000/mcp') {
        this.mcpEndpoint = mcpEndpoint;
        this.requestId = 1;
        this.maxRetries = 3;
        this.retryDelay = 1000; // ms
    }

    /**
     * Call Apollo MCP tool with retry logic
     */
    async callMCPTool(toolName, params) {
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                const response = await fetch(this.mcpEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: "2.0",
                        id: this.requestId++,
                        method: "tools/call",
                        params: {
                            name: toolName,
                            arguments: params
                        }
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                
                if (result.error) {
                    throw new Error(`MCP Error: ${result.error.message}`);
                }

                // Parse the content from MCP response
                const content = result.result?.content?.[0]?.text;
                if (content) {
                    try {
                        return JSON.parse(content);
                    } catch (e) {
                        // Return raw text if not JSON
                        return { raw_content: content };
                    }
                }

                return result.result;

            } catch (error) {
                console.log(`Apollo MCP call attempt ${attempt} failed:`, error.message);
                
                if (attempt === this.maxRetries) {
                    throw new Error(`Apollo MCP failed after ${this.maxRetries} attempts: ${error.message}`);
                }
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempt));
            }
        }
    }

    /**
     * Analyze vacancy with Apollo intelligence
     */
    async analyzeVacancy(vacancyText, companyName = null, jobTitle = null) {
        return await this.callMCPTool('apollo_analyze_vacancy', {
            vacancyText,
            companyName,
            jobTitle
        });
    }

    /**
     * Enrich company data
     */
    async enrichCompany(domain) {
        return await this.callMCPTool('apollo_enrich_organization', {
            domain
        });
    }

    /**
     * Search for HR contacts
     */
    async findHRContacts(companyDomain, titles = ['HR Director', 'HR Manager', 'Talent Acquisition']) {
        return await this.callMCPTool('apollo_search_people', {
            qOrganizationDomains: [companyDomain],
            personTitles: titles,
            perPage: 10
        });
    }

    /**
     * Search for decision makers
     */
    async findDecisionMakers(companyDomain) {
        return await this.callMCPTool('apollo_search_people', {
            qOrganizationDomains: [companyDomain],
            personSeniorities: ['c_suite', 'vp', 'director'],
            perPage: 5
        });
    }
}

// =============================================================================
// ZAPIER WORKFLOW FUNCTIONS
// =============================================================================

/**
 * ZAPIER STEP 1: Enhanced Typeform Processing
 * Gebruikt Apollo MCP voor complete intelligence gathering
 */
async function zapierStep1_EnhancedTypeformProcessing(inputData) {
    console.log('🚀 Starting Apollo-enhanced Typeform processing...');
    
    const apollo = new ZapierApolloMCPClient();
    const startTime = Date.now();
    
    try {
        // Extract data from Typeform
        const formData = {
            firstName: inputData.first_name || inputData['answers.fR8Baj3xlH5M'],
            lastName: inputData.last_name || inputData['answers.last_name'],
            email: inputData.email || inputData['answers.email'],
            phone: inputData.phone || inputData['answers.phone'],
            companyName: inputData.company_name || inputData['answers.OpCFtxbTUqB9'],
            jobTitle: inputData.job_title || inputData['answers.job_title'],
            vacancyText: inputData.vacancy_text || inputData['answers.w6gOgcsW6qJJ'],
            companyDomain: extractDomain(inputData.email) || inputData.company_domain
        };

        console.log(`Processing for: ${formData.companyName} - ${formData.jobTitle}`);

        // Parallel Apollo intelligence gathering
        const apolloTasks = [];

        // Task 1: Vacancy Analysis
        apolloTasks.push(
            apollo.analyzeVacancy(
                formData.vacancyText,
                formData.companyName,
                formData.jobTitle
            ).then(result => ({ type: 'vacancy_analysis', data: result }))
        );

        // Task 2: Company Enrichment (if domain available)
        if (formData.companyDomain) {
            apolloTasks.push(
                apollo.enrichCompany(formData.companyDomain)
                    .then(result => ({ type: 'company_data', data: result }))
            );

            // Task 3: HR Contacts
            apolloTasks.push(
                apollo.findHRContacts(formData.companyDomain)
                    .then(result => ({ type: 'hr_contacts', data: result }))
            );

            // Task 4: Decision Makers
            apolloTasks.push(
                apollo.findDecisionMakers(formData.companyDomain)
                    .then(result => ({ type: 'decision_makers', data: result }))
            );
        }

        // Execute all Apollo tasks in parallel
        const apolloResults = await Promise.allSettled(apolloTasks);
        
        // Process results
        const intelligence = {
            vacancy_analysis: null,
            company_data: null,
            hr_contacts: null,
            decision_makers: null,
            apollo_enhanced: true,
            processing_time_ms: Date.now() - startTime
        };

        apolloResults.forEach(result => {
            if (result.status === 'fulfilled' && result.value) {
                intelligence[result.value.type] = result.value.data;
            }
        });

        // Calculate lead score
        const leadScore = calculateEnhancedLeadScore(formData, intelligence);
        
        // Enhanced output for next Zapier step
        const output = {
            // Original form data
            ...formData,
            
            // Apollo intelligence
            apollo_vacancy_score: intelligence.vacancy_analysis?.score || 0,
            apollo_lead_score: leadScore,
            apollo_company_employees: intelligence.company_data?.organization?.estimatedNumEmployees || 'Unknown',
            apollo_company_industry: intelligence.company_data?.organization?.industry || 'Unknown',
            apollo_company_revenue: intelligence.company_data?.organization?.annualRevenue || 'Unknown',
            apollo_hr_contacts_found: intelligence.hr_contacts?.count || 0,
            apollo_decision_makers_found: intelligence.decision_makers?.count || 0,
            apollo_processing_time: intelligence.processing_time_ms,
            
            // Full analysis for email
            apollo_full_analysis: intelligence.vacancy_analysis?.analysis || '',
            apollo_conversion_estimate: intelligence.vacancy_analysis?.conversionEstimate || '',
            
            // Enhanced metadata
            apollo_enhanced: true,
            apollo_timestamp: new Date().toISOString(),
            apollo_success_rate: calculateSuccessRate(apolloResults),
            
            // Priority routing
            priority_level: leadScore >= 80 ? 'HIGH' : leadScore >= 60 ? 'MEDIUM' : 'LOW',
            auto_qualify: leadScore >= 70,
            immediate_callback: leadScore >= 85
        };

        console.log(`✅ Apollo processing complete. Lead score: ${leadScore}/100`);
        console.log(`⏱️ Processing time: ${intelligence.processing_time_ms}ms`);
        
        return output;

    } catch (error) {
        console.error('❌ Apollo processing failed:', error);
        
        // Graceful degradation - return original data with error info
        return {
            ...inputData,
            apollo_enhanced: false,
            apollo_error: error.message,
            apollo_fallback: true,
            priority_level: 'MEDIUM',
            processing_time: Date.now() - startTime
        };
    }
}

/**
 * ZAPIER STEP 2: Enhanced Pipedrive Deal Creation
 * Creates deals with Apollo intelligence
 */
async function zapierStep2_EnhancedPipedriveCreation(inputData) {
    console.log('💼 Creating enhanced Pipedrive deal with Apollo data...');
    
    try {
        // Enhanced deal title with intelligence
        const dealTitle = `${inputData.apollo_lead_score}/100 - ${inputData.company_name || 'Unknown'} - ${inputData.job_title || 'Vacature'}`;
        
        // Custom fields with Apollo data
        const customFields = {
            // Apollo intelligence
            'apollo_lead_score': inputData.apollo_lead_score || 0,
            'vacancy_quality_score': inputData.apollo_vacancy_score || 0,
            'company_employees': inputData.apollo_company_employees,
            'company_industry': inputData.apollo_company_industry,
            'hr_contacts_found': inputData.apollo_hr_contacts_found || 0,
            'decision_makers_found': inputData.apollo_decision_makers_found || 0,
            'apollo_processing_time': inputData.apollo_processing_time || 0,
            
            // Qualification flags
            'auto_qualified': inputData.auto_qualify || false,
            'priority_level': inputData.priority_level || 'MEDIUM',
            'immediate_callback_needed': inputData.immediate_callback || false,
            'apollo_enhanced': inputData.apollo_enhanced || false
        };

        // Deal value based on lead score
        const dealValue = calculateDealValue(inputData.apollo_lead_score || 50);
        
        // Priority stage assignment
        const stageId = getStageByPriority(inputData.priority_level);
        
        const dealData = {
            title: dealTitle,
            value: dealValue,
            currency: 'EUR',
            stage_id: stageId,
            pipeline_id: 3, // Vacature analyse pipeline
            person_name: `${inputData.firstName} ${inputData.lastName}`.trim(),
            person_email: inputData.email,
            person_phone: inputData.phone,
            org_name: inputData.company_name,
            custom_fields: customFields,
            notes: generateApolloNote(inputData)
        };

        console.log(`💰 Deal value: €${dealValue} (score: ${inputData.apollo_lead_score})`);
        console.log(`📊 Priority: ${inputData.priority_level} → Stage: ${stageId}`);
        
        return dealData;

    } catch (error) {
        console.error('❌ Enhanced Pipedrive creation failed:', error);
        throw error;
    }
}

/**
 * ZAPIER STEP 3: Hyper-Personalized Email Generation
 * Creates context-aware emails with Apollo intelligence
 */
async function zapierStep3_HyperPersonalizedEmail(inputData) {
    console.log('📧 Generating hyper-personalized email with Apollo context...');
    
    try {
        const emailTemplate = generateHyperPersonalizedEmailTemplate(inputData);
        
        const emailData = {
            to: inputData.email,
            subject: generatePersonalizedSubject(inputData),
            html_body: emailTemplate,
            attachments: [],
            
            // Email metadata for tracking
            apollo_enhanced: inputData.apollo_enhanced || false,
            lead_score: inputData.apollo_lead_score || 0,
            priority_level: inputData.priority_level || 'MEDIUM',
            personalization_level: calculatePersonalizationLevel(inputData)
        };

        console.log(`📊 Personalization level: ${emailData.personalization_level}/10`);
        console.log(`🎯 Email optimized for ${inputData.priority_level} priority lead`);
        
        return emailData;

    } catch (error) {
        console.error('❌ Email generation failed:', error);
        throw error;
    }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function extractDomain(email) {
    if (!email) return null;
    const match = email.match(/@([^.]+\.[^.]+)$/);
    return match ? match[1] : null;
}

function calculateEnhancedLeadScore(formData, intelligence) {
    let score = 0;
    
    // Vacancy quality (0-40 points)
    const vacancyScore = intelligence.vacancy_analysis?.score || 0;
    score += Math.round(vacancyScore * 4);
    
    // Company size (0-25 points)
    const employees = intelligence.company_data?.organization?.estimatedNumEmployees || 0;
    if (employees > 500) score += 25;
    else if (employees > 200) score += 20;
    else if (employees > 50) score += 15;
    else if (employees > 10) score += 10;
    
    // Industry priority (0-15 points)
    const industry = intelligence.company_data?.organization?.industry || '';
    const priorityIndustries = ['Technology', 'Healthcare', 'Manufacturing', 'Financial'];
    if (priorityIndustries.some(ind => industry.includes(ind))) {
        score += 15;
    }
    
    // Contact availability (0-10 points)
    const hrContacts = intelligence.hr_contacts?.count || 0;
    score += Math.min(hrContacts * 2, 10);
    
    // Decision makers (0-10 points)
    const decisionMakers = intelligence.decision_makers?.count || 0;
    score += Math.min(decisionMakers * 2, 10);
    
    return Math.min(score, 100);
}

function calculateSuccessRate(results) {
    const successful = results.filter(r => r.status === 'fulfilled').length;
    return Math.round((successful / results.length) * 100);
}

function calculateDealValue(leadScore) {
    if (leadScore >= 85) return 25000;
    if (leadScore >= 70) return 20000;
    if (leadScore >= 55) return 15000;
    if (leadScore >= 40) return 12000;
    return 10000;
}

function getStageByPriority(priority) {
    switch (priority) {
        case 'HIGH': return 16; // Hot lead stage
        case 'MEDIUM': return 15; // Standard stage  
        case 'LOW': return 14; // Nurture stage
        default: return 15;
    }
}

function generateApolloNote(inputData) {
    return `🤖 APOLLO INTELLIGENCE RAPPORT

LEAD SCORE: ${inputData.apollo_lead_score || 0}/100
PRIORITY: ${inputData.priority_level || 'MEDIUM'}
PROCESSING TIME: ${inputData.apollo_processing_time || 0}ms

📊 BEDRIJFSINZICHTEN:
- Werknemers: ${inputData.apollo_company_employees || 'Unknown'}
- Sector: ${inputData.apollo_company_industry || 'Unknown'}
- HR Contacten: ${inputData.apollo_hr_contacts_found || 0}
- Decision Makers: ${inputData.apollo_decision_makers_found || 0}

📝 VACATURE ANALYSE:
Score: ${inputData.apollo_vacancy_score || 0}/10
${inputData.apollo_conversion_estimate || 'Geen schatting beschikbaar'}

🎯 ACTIE:
${inputData.auto_qualify ? '✅ AUTO-GEKWALIFICEERD' : '⏳ HANDMATIGE REVIEW'}
${inputData.immediate_callback ? '📞 DIRECTE TERUGBELACTIE VEREIST' : ''}

Apollo Enhanced: ${inputData.apollo_enhanced ? '✅' : '❌'}
Timestamp: ${inputData.apollo_timestamp || new Date().toISOString()}`;
}

function generatePersonalizedSubject(inputData) {
    const score = inputData.apollo_lead_score || 0;
    const company = inputData.company_name || 'uw bedrijf';
    
    if (score >= 85) {
        return `🎯 Urgent: ${company} - 40% meer kandidaten binnen 8 dagen`;
    } else if (score >= 70) {
        return `🚀 ${company}: Jouw vacature-analyse + 3 concrete verbeterpunten`;
    } else if (score >= 55) {
        return `📊 ${company}: Gratis vacature-optimalisatie gereed`;
    } else {
        return `📈 ${company}: Kandidaattekort oplossen - gratis analyse`;
    }
}

function generateHyperPersonalizedEmailTemplate(inputData) {
    const score = inputData.apollo_lead_score || 0;
    const company = inputData.company_name || 'uw bedrijf';
    const industry = inputData.apollo_company_industry || 'uw sector';
    const employees = inputData.apollo_company_employees || 'onbekend aantal';
    
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apollo-Enhanced Vacature Analyse</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 24px;">🎯 Jouw Apollo-Enhanced Vacature Analyse</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">${company} • Lead Score: ${score}/100</p>
    </div>

    <div style="background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin-bottom: 20px;">
        <h2 style="color: #667eea; margin-top: 0;">Beste ${inputData.firstName || 'Collega'},</h2>
        <p>Bedankt voor je vacature-analyse aanvraag! Onze Apollo AI heeft jouw vacature geanalyseerd en krachtige bedrijfsinzichten verzameld.</p>
    </div>

    <div style="background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <h3 style="color: #495057; border-bottom: 2px solid #f8f9fa; padding-bottom: 10px;">🏢 Bedrijfsinzichten (Apollo Intelligence)</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px 0; font-weight: bold;">Bedrijf:</td><td style="padding: 8px 0;">${company}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Sector:</td><td style="padding: 8px 0;">${industry}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Werknemers:</td><td style="padding: 8px 0;">${employees}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">HR Contacten:</td><td style="padding: 8px 0;">${inputData.apollo_hr_contacts_found || 0} gevonden</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Decision Makers:</td><td style="padding: 8px 0;">${inputData.apollo_decision_makers_found || 0} geïdentificeerd</td></tr>
        </table>
    </div>

    <div style="background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <h3 style="color: #495057; border-bottom: 2px solid #f8f9fa; padding-bottom: 10px;">📊 Vacature Analyse Resultaten</h3>
        <div style="background: ${score >= 70 ? '#d4edda' : score >= 50 ? '#fff3cd' : '#f8d7da'}; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
            <h4 style="margin: 0; color: ${score >= 70 ? '#155724' : score >= 50 ? '#856404' : '#721c24'};">
                Score: ${inputData.apollo_vacancy_score || 0}/10 ⭐
            </h4>
            <p style="margin: 5px 0 0 0; color: ${score >= 70 ? '#155724' : score >= 50 ? '#856404' : '#721c24'};">
                ${score >= 70 ? 'Uitstekende vacaturetekst!' : score >= 50 ? 'Goede basis, kan geoptimaliseerd worden.' : 'Veel verbeterpotentieel aanwezig.'}
            </p>
        </div>
        
        <div style="white-space: pre-line; background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 14px;">
${inputData.apollo_full_analysis || 'Analyse wordt nog verwerkt...'}
        </div>
    </div>

    <div style="background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <h3 style="color: #495057;">🎯 Verwachte Resultaten</h3>
        ${inputData.apollo_conversion_estimate || 'Verwacht 20-40% meer relevante sollicitaties binnen 2 weken.'}
    </div>

    <div style="text-align: center; margin: 30px 0;">
        <a href="https://calendly.com/wouter-arts-/vacature-analyse-advies" 
           style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 10px;">
            📅 Plan Gratis Adviesgesprek
        </a>
        <a href="https://wa.me/31614314593" 
           style="display: inline-block; background: #25D366; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 10px;">
            💬 Direct WhatsApp
        </a>
    </div>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; font-size: 12px; color: #6c757d;">
        <p style="margin: 0;">🤖 Deze analyse is gegenereerd met Apollo AI Intelligence</p>
        <p style="margin: 5px 0 0 0;">Processing tijd: ${inputData.apollo_processing_time || 0}ms | Lead Score: ${score}/100</p>
        <p style="margin: 5px 0 0 0;">Recruitin B.V. • kandidatentekort.nl • Gebaseerd op CBS/UWV data Q4 2024</p>
    </div>

</body>
</html>
    `;
}

function calculatePersonalizationLevel(inputData) {
    let level = 5; // Base level
    
    if (inputData.apollo_company_industry && inputData.apollo_company_industry !== 'Unknown') level += 1;
    if (inputData.apollo_company_employees && inputData.apollo_company_employees !== 'Unknown') level += 1;
    if (inputData.apollo_hr_contacts_found > 0) level += 1;
    if (inputData.apollo_decision_makers_found > 0) level += 1;
    if (inputData.apollo_lead_score >= 70) level += 1;
    
    return Math.min(level, 10);
}

// =============================================================================
// ZAPIER EXPORT FUNCTIONS
// =============================================================================

// Export for Zapier Code Steps
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        zapierStep1_EnhancedTypeformProcessing,
        zapierStep2_EnhancedPipedriveCreation,
        zapierStep3_HyperPersonalizedEmail,
        ZapierApolloMCPClient
    };
}

// Test function for development
async function testZapierApolloIntegration() {
    console.log('🧪 Testing Zapier-Apollo MCP Integration...');
    
    const testData = {
        first_name: 'Test',
        last_name: 'User',
        email: 'test@techbedrijf.nl',
        phone: '+31612345678',
        company_name: 'Tech Innovatie B.V.',
        job_title: 'Senior Developer',
        vacancy_text: 'Wij zoeken een ervaren Python developer...'
    };
    
    try {
        const result = await zapierStep1_EnhancedTypeformProcessing(testData);
        console.log('✅ Test successful:', result);
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Uncomment to test locally
// testZapierApolloIntegration();
/**
 * Pipedrive Client Service
 *
 * Provides a centralized interface to the Pipedrive CRM API.
 * Uses Pipedrive SDK v30.x with OpenAPI generated clients.
 *
 * @module pipedrive-service
 */

require('dotenv').config();
const { v1: pipedrive } = require('pipedrive');

// Initialize API configuration with API key
const config = new pipedrive.Configuration({
  apiKey: process.env.PIPEDRIVE_API_TOKEN
});

// API instances
const dealsApi = new pipedrive.DealsApi(config);
const personsApi = new pipedrive.PersonsApi(config);
const organizationsApi = new pipedrive.OrganizationsApi(config);
const pipelinesApi = new pipedrive.PipelinesApi(config);
const stagesApi = new pipedrive.StagesApi(config);
const activitiesApi = new pipedrive.ActivitiesApi(config);
const usersApi = new pipedrive.UsersApi(config);

/**
 * Pipeline IDs used in the system
 */
const PIPELINES = {
  CORPORATE_RECRUITER: 14,
  VACATURE_ANALYSE: 4,
  RECRUITMENT_APK: 2,
  JOBDIGGER_AUTOMATION: 12,
  DEFAULT: 1
};

/**
 * Stage IDs for each pipeline
 */
const STAGES = {
  VACATURE_ANALYSE: {
    LEAD: 19,
    GEKWALIFICEERD: 21,
    GESPREK: 22,
    PROPOSITIE: 23,
    CONTRACT: 24
  },
  CORPORATE_RECRUITER: {
    NIEUW_LEAD: 168,
    COLD_EMAIL_1: 169,
    FOLLOW_UP_2: 170,
    FOLLOW_UP_3: 171,
    REPLIED: 172,
    QUALIFIED: 173,
    NOT_INTERESTED: 174
  }
};

/**
 * Test the API connection
 * @returns {Promise<Object>} Current user info
 */
async function testConnection() {
  try {
    const response = await usersApi.getCurrentUser();
    console.log('Pipedrive connection successful!');
    console.log('Logged in as:', response.data.name, `(${response.data.email})`);
    return response.data;
  } catch (error) {
    console.error('Pipedrive connection failed:', error.message);
    throw error;
  }
}

/**
 * Get all pipelines
 * @returns {Promise<Array>} List of pipelines
 */
async function getPipelines() {
  try {
    const response = await pipelinesApi.getPipelines();
    return response.data || [];
  } catch (error) {
    console.error('Error fetching pipelines:', error.message);
    throw error;
  }
}

/**
 * Get stages for a pipeline
 * @param {number} pipelineId - Pipeline ID
 * @returns {Promise<Array>} List of stages
 */
async function getStages(pipelineId) {
  try {
    const response = await stagesApi.getStages({ pipelineId });
    return response.data || [];
  } catch (error) {
    console.error('Error fetching stages:', error.message);
    throw error;
  }
}

/**
 * Create a new deal
 * @param {Object} dealData - Deal information
 * @param {string} dealData.title - Deal title
 * @param {number} [dealData.pipelineId] - Pipeline ID (default: VACATURE_ANALYSE)
 * @param {number} [dealData.stageId] - Stage ID
 * @param {number} [dealData.personId] - Associated person ID
 * @param {number} [dealData.orgId] - Associated organization ID
 * @param {number} [dealData.value] - Deal value
 * @param {string} [dealData.currency] - Currency code (default: EUR)
 * @returns {Promise<Object>} Created deal
 */
async function createDeal(dealData) {
  try {
    const newDeal = {
      title: dealData.title,
      pipeline_id: dealData.pipelineId || PIPELINES.VACATURE_ANALYSE,
      stage_id: dealData.stageId,
      person_id: dealData.personId,
      org_id: dealData.orgId,
      value: dealData.value,
      currency: dealData.currency || 'EUR'
    };

    const response = await dealsApi.addDeal({ AddDealRequest: newDeal });
    console.log('Deal created:', response.data.id, '-', response.data.title);
    return response.data;
  } catch (error) {
    console.error('Error creating deal:', error.message);
    throw error;
  }
}

/**
 * Get a deal by ID
 * @param {number} dealId - Deal ID
 * @returns {Promise<Object>} Deal details
 */
async function getDeal(dealId) {
  try {
    const response = await dealsApi.getDeal({ id: dealId });
    return response.data;
  } catch (error) {
    console.error('Error fetching deal:', error.message);
    throw error;
  }
}

/**
 * Update a deal
 * @param {number} dealId - Deal ID
 * @param {Object} updateData - Fields to update
 * @returns {Promise<Object>} Updated deal
 */
async function updateDeal(dealId, updateData) {
  try {
    const response = await dealsApi.updateDeal({ id: dealId, UpdateDealRequest: updateData });
    console.log('Deal updated:', dealId);
    return response.data;
  } catch (error) {
    console.error('Error updating deal:', error.message);
    throw error;
  }
}

/**
 * Move deal to a different stage
 * @param {number} dealId - Deal ID
 * @param {number} stageId - New stage ID
 * @returns {Promise<Object>} Updated deal
 */
async function moveDealToStage(dealId, stageId) {
  return updateDeal(dealId, { stage_id: stageId });
}

/**
 * Get deals from a specific pipeline
 * @param {number} pipelineId - Pipeline ID
 * @param {Object} [options] - Query options
 * @param {string} [options.status] - Deal status (open, won, lost, all_not_deleted)
 * @param {number} [options.limit] - Max results (default: 100)
 * @returns {Promise<Array>} List of deals
 */
async function getDealsInPipeline(pipelineId, options = {}) {
  try {
    const response = await dealsApi.getDeals({
      pipelineId: pipelineId,
      status: options.status || 'open',
      start: 0,
      limit: options.limit || 100,
      sort: 'add_time DESC'
    });
    return response.data || [];
  } catch (error) {
    console.error('Error fetching deals:', error.message);
    throw error;
  }
}

/**
 * Create a new person
 * @param {Object} personData - Person information
 * @param {string} personData.name - Full name
 * @param {string} [personData.email] - Email address
 * @param {string} [personData.phone] - Phone number
 * @param {number} [personData.orgId] - Associated organization ID
 * @returns {Promise<Object>} Created person
 */
async function createPerson(personData) {
  try {
    const newPerson = {
      name: personData.name,
      email: personData.email ? [{ value: personData.email, primary: true }] : undefined,
      phone: personData.phone ? [{ value: personData.phone, primary: true }] : undefined,
      org_id: personData.orgId
    };

    const response = await personsApi.addPerson({ AddPersonRequest: newPerson });
    console.log('Person created:', response.data.id, '-', response.data.name);
    return response.data;
  } catch (error) {
    console.error('Error creating person:', error.message);
    throw error;
  }
}

/**
 * Search for a person by email
 * @param {string} email - Email to search
 * @returns {Promise<Object|null>} Found person or null
 */
async function findPersonByEmail(email) {
  try {
    const response = await personsApi.searchPersons({
      term: email,
      fields: 'email',
      exactMatch: true
    });
    return response.data?.items?.[0]?.item || null;
  } catch (error) {
    console.error('Error searching person:', error.message);
    return null;
  }
}

/**
 * Create a new organization
 * @param {Object} orgData - Organization information
 * @param {string} orgData.name - Organization name
 * @param {string} [orgData.address] - Address
 * @returns {Promise<Object>} Created organization
 */
async function createOrganization(orgData) {
  try {
    const newOrg = {
      name: orgData.name,
      address: orgData.address
    };

    const response = await organizationsApi.addOrganization({ AddOrganizationRequest: newOrg });
    console.log('Organization created:', response.data.id, '-', response.data.name);
    return response.data;
  } catch (error) {
    console.error('Error creating organization:', error.message);
    throw error;
  }
}

/**
 * Search for an organization by name
 * @param {string} name - Name to search
 * @returns {Promise<Object|null>} Found organization or null
 */
async function findOrganizationByName(name) {
  try {
    const response = await organizationsApi.searchOrganization({
      term: name,
      exactMatch: false
    });
    return response.data?.items?.[0]?.item || null;
  } catch (error) {
    console.error('Error searching organization:', error.message);
    return null;
  }
}

/**
 * Create an activity for a deal
 * @param {Object} activityData - Activity information
 * @param {string} activityData.subject - Activity subject
 * @param {string} activityData.type - Activity type (call, email, meeting, etc.)
 * @param {number} [activityData.dealId] - Associated deal ID
 * @param {number} [activityData.personId] - Associated person ID
 * @param {string} [activityData.dueDate] - Due date (YYYY-MM-DD)
 * @param {string} [activityData.dueTime] - Due time (HH:MM)
 * @param {string} [activityData.note] - Activity note
 * @returns {Promise<Object>} Created activity
 */
async function createActivity(activityData) {
  try {
    const newActivity = {
      subject: activityData.subject,
      type: activityData.type,
      deal_id: activityData.dealId,
      person_id: activityData.personId,
      due_date: activityData.dueDate,
      due_time: activityData.dueTime,
      note: activityData.note
    };

    const response = await activitiesApi.addActivity({ AddActivityRequest: newActivity });
    console.log('Activity created:', response.data.id, '-', response.data.subject);
    return response.data;
  } catch (error) {
    console.error('Error creating activity:', error.message);
    throw error;
  }
}

/**
 * Create a complete lead with organization, person, and deal
 * @param {Object} leadData - Complete lead data
 * @param {string} leadData.companyName - Company name
 * @param {string} leadData.contactName - Contact person name
 * @param {string} [leadData.email] - Contact email
 * @param {string} [leadData.phone] - Contact phone
 * @param {string} [leadData.dealTitle] - Deal title (default: auto-generated)
 * @param {number} [leadData.pipelineId] - Pipeline ID
 * @param {number} [leadData.stageId] - Stage ID
 * @returns {Promise<Object>} Created deal with org and person IDs
 */
async function createCompleteLead(leadData) {
  try {
    // 1. Create or find organization
    let org = await findOrganizationByName(leadData.companyName);
    if (!org) {
      org = await createOrganization({ name: leadData.companyName });
    }

    // 2. Create or find person
    let person = leadData.email ? await findPersonByEmail(leadData.email) : null;
    if (!person) {
      person = await createPerson({
        name: leadData.contactName,
        email: leadData.email,
        phone: leadData.phone,
        orgId: org.id
      });
    }

    // 3. Create deal
    const deal = await createDeal({
      title: leadData.dealTitle || `${leadData.companyName} - ${leadData.contactName}`,
      pipelineId: leadData.pipelineId || PIPELINES.VACATURE_ANALYSE,
      stageId: leadData.stageId,
      personId: person.id,
      orgId: org.id
    });

    return {
      deal,
      person,
      organization: org
    };
  } catch (error) {
    console.error('Error creating complete lead:', error.message);
    throw error;
  }
}

// Export service
module.exports = {
  // Constants
  PIPELINES,
  STAGES,

  // Connection
  testConnection,

  // Pipelines & Stages
  getPipelines,
  getStages,

  // Deals
  createDeal,
  getDeal,
  updateDeal,
  moveDealToStage,
  getDealsInPipeline,

  // Persons
  createPerson,
  findPersonByEmail,

  // Organizations
  createOrganization,
  findOrganizationByName,

  // Activities
  createActivity,

  // Complete workflows
  createCompleteLead,

  // Raw API access for advanced usage
  config,
  dealsApi,
  personsApi,
  organizationsApi,
  pipelinesApi,
  stagesApi,
  activitiesApi,
  usersApi
};

// Run test if executed directly
if (require.main === module) {
  testConnection()
    .then(user => {
      console.log('\n--- Testing getPipelines ---');
      return getPipelines();
    })
    .then(pipelines => {
      console.log('Found', pipelines.length, 'pipelines:');
      pipelines.forEach(p => console.log(` - ${p.id}: ${p.name}`));
    })
    .catch(err => {
      console.error('Test failed:', err.message);
      process.exit(1);
    });
}

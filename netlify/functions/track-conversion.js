// Facebook Conversions API Handler
// Tracks server-side events to improve iOS 14.5+ attribution

exports.handler = async (event, context) => {
  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method Not Allowed' })
    };
  }

  // Parse request body
  let data;
  try {
    data = JSON.parse(event.body);
  } catch (error) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: 'Invalid JSON payload' })
    };
  }

  // Get environment variables
  const FACEBOOK_API_TOKEN = process.env.FACEBOOK_API_TOKEN;
  const PIXEL_ID = process.env.FACEBOOK_PIXEL_ID || '238226887541404';
  
  if (!FACEBOOK_API_TOKEN) {
    console.error('Missing FACEBOOK_API_TOKEN environment variable');
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Server configuration error' })
    };
  }

  // Extract event data
  const {
    event_name = 'Lead',
    event_time = Math.floor(Date.now() / 1000),
    email,
    phone,
    action_source = 'website',
    event_source_url = event.headers.referer || 'https://kandidatentekort.nl',
    user_agent = event.headers['user-agent'],
    ip_address = event.headers['x-forwarded-for'] || event.headers['client-ip']
  } = data;

  // Hash user data for privacy
  const crypto = require('crypto');
  const hashData = (data) => {
    if (!data) return undefined;
    return crypto.createHash('sha256').update(data.toLowerCase().trim()).digest('hex');
  };

  // Build server event
  const serverEvent = {
    event_name,
    event_time,
    action_source,
    event_source_url,
    user_data: {
      em: hashData(email),
      ph: hashData(phone),
      client_ip_address: ip_address,
      client_user_agent: user_agent,
      fbc: getCookie(event.headers.cookie, '_fbc'),
      fbp: getCookie(event.headers.cookie, '_fbp')
    },
    custom_data: data.custom_data || {}
  };

  // Send to Facebook Conversions API
  try {
    const response = await fetch(
      `https://graph.facebook.com/v18.0/${PIXEL_ID}/events`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          data: [serverEvent],
          access_token: FACEBOOK_API_TOKEN,
          test_event_code: process.env.TEST_EVENT_CODE // Optional: for testing in Events Manager
        })
      }
    );

    const result = await response.json();

    if (!response.ok) {
      console.error('Facebook API error:', result);
      return {
        statusCode: 500,
        body: JSON.stringify({ 
          error: 'Failed to track event',
          details: result.error?.message 
        })
      };
    }

    // Success response
    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type'
      },
      body: JSON.stringify({
        success: true,
        event_name,
        events_received: result.events_received,
        fbtrace_id: result.fbtrace_id
      })
    };

  } catch (error) {
    console.error('Conversions API error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ 
        error: 'Internal server error',
        message: error.message 
      })
    };
  }
};

// Helper function to extract cookie value
function getCookie(cookieString, name) {
  if (!cookieString) return undefined;
  const value = `; ${cookieString}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return undefined;
}
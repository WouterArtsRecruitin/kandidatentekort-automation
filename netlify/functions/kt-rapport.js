/**
 * Netlify Function: KT Rapport Proxy
 * Fetches hosted rapport HTML from Supabase Storage and serves as text/html
 * (Supabase serves HTML as text/plain for security, so we proxy it)
 */

const { createClient } = require("@supabase/supabase-js");

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;

exports.handler = async (event) => {
  try {
    const path = event.queryStringParameters?.path;

    if (!path) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: "Missing 'path' parameter" }),
      };
    }

    if (!supabaseUrl || !supabaseAnonKey) {
      return {
        statusCode: 500,
        body: JSON.stringify({ error: "Missing Supabase credentials" }),
      };
    }

    // Initialize Supabase client
    const supabase = createClient(supabaseUrl, supabaseAnonKey);

    // Fetch from Storage
    const { data, error } = await supabase.storage
      .from("kt-assets")
      .download(path);

    if (error) {
      console.error(`❌ Download error: ${error.message}`);
      return {
        statusCode: 404,
        body: JSON.stringify({ error: "Rapport not found" }),
      };
    }

    // Convert blob to text
    const htmlContent = await data.text();

    // Return with text/html content type
    return {
      statusCode: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "public, max-age=3600",
      },
      body: htmlContent,
    };
  } catch (err) {
    console.error(`❌ Error: ${err.message}`);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: err.message }),
    };
  }
};

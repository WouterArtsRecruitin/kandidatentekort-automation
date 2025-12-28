# Netlify Functions - Kandidatentekort

## track-conversion.js

Facebook Conversions API implementation for server-side event tracking.

### Environment Variables Required:

```
FACEBOOK_API_TOKEN=your_facebook_api_token
FACEBOOK_PIXEL_ID=238226887541404
TEST_EVENT_CODE=TEST12345 (optional, for testing)
```

### Usage:

```javascript
// From frontend
fetch('/.netlify/functions/track-conversion', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    event_name: 'Lead',
    email: 'user@example.com',
    phone: '+31612345678',
    custom_data: {
      value: 0,
      currency: 'EUR'
    }
  })
});
```

### Supported Events:

- PageView
- Lead
- CompleteRegistration
- Contact
- Schedule
- Purchase

### Testing:

1. Set TEST_EVENT_CODE in environment
2. Go to Facebook Events Manager > Test Events
3. Enter the test code
4. Send test events
5. Verify they appear in the test interface

### GDPR Compliance:

- All PII is hashed using SHA256 before sending
- IP addresses are forwarded for geographic matching
- Cookie consent is assumed (check frontend implementation)
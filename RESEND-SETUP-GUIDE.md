# 📧 Resend Email Setup Guide for kandidatentekort.nl

## Overview
This guide walks you through setting up Resend email service for the kandidatentekort.nl domain.

## 1. Resend Account Setup

1. **Create Resend Account**
   - Go to [https://resend.com/signup](https://resend.com/signup)
   - Sign up with your work email
   - Verify your email address

2. **Get API Key**
   - Navigate to API Keys: [https://resend.com/api-keys](https://resend.com/api-keys)
   - Click "Create API Key"
   - Name: "kandidatentekort-production"
   - Permissions: "Full Access" 
   - Copy the API key (starts with `re_`)

3. **Add Domain**
   - Go to Domains: [https://resend.com/domains](https://resend.com/domains)
   - Click "Add Domain"
   - Enter: `kandidatentekort.nl`
   - Region: Europe (eu-west-1) for GDPR compliance

## 2. DNS Records Configuration

Add these DNS records to your kandidatentekort.nl domain:

### SPF Record (TXT)
```
Type: TXT
Name: @ (or kandidatentekort.nl)
Value: "v=spf1 include:amazonses.com ~all"
TTL: 3600
```

### DKIM Records (CNAME)
You'll receive 3 DKIM records from Resend. They look like:

```
Type: CNAME
Name: resend._domainkey
Value: resend._domainkey.kandidatentekort.nl.dkim.resend.com
TTL: 3600
```

```
Type: CNAME
Name: resend2._domainkey
Value: resend2._domainkey.kandidatentekort.nl.dkim.resend.com
TTL: 3600
```

```
Type: CNAME
Name: resend3._domainkey
Value: resend3._domainkey.kandidatentekort.nl.dkim.resend.com
TTL: 3600
```

### DMARC Record (TXT) - Optional but Recommended
```
Type: TXT
Name: _dmarc
Value: "v=DMARC1; p=none; rua=mailto:dmarc@kandidatentekort.nl; ruf=mailto:dmarc@kandidatentekort.nl; sp=none; aspf=r; adkim=r;"
TTL: 3600
```

### MX Records (If receiving email)
```
Type: MX
Name: @ (or kandidatentekort.nl)
Priority: 10
Value: feedback-smtp.eu-west-1.amazonses.com
TTL: 3600
```

## 3. Environment Variables

Update your `.env` file:

```bash
# Remove old Gmail SMTP settings
# GMAIL_USER=wouter@recruitin.nl
# GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Add Resend configuration
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=noreply@kandidatentekort.nl
RESEND_FROM_NAME=Kandidatentekort

# Optional: Different sender addresses
RESEND_REPORTS_EMAIL=rapporten@kandidatentekort.nl
RESEND_NOTIFICATIONS_EMAIL=notificaties@kandidatentekort.nl
RESEND_SUPPORT_EMAIL=support@kandidatentekort.nl
```

## 4. Verify Domain

After adding DNS records:

1. Wait 5-10 minutes for DNS propagation
2. Go back to Resend dashboard
3. Click "Verify DNS Records" 
4. All records should show green checkmarks

## 5. Testing

Use the test script below to verify your setup:

```javascript
const EmailService = require('./email-service');

async function testResendSetup() {
    const emailService = new EmailService(process.env.RESEND_API_KEY, {
        defaultFrom: process.env.RESEND_FROM_EMAIL
    });

    // 1. Verify domain
    console.log('Verifying domain...');
    const domainStatus = await emailService.verifyDomain();
    console.log('Domain status:', domainStatus);

    if (!domainStatus.verified) {
        console.error('❌ Domain not verified. Please check DNS records.');
        return;
    }

    // 2. Send test email
    console.log('\\nSending test email...');
    const result = await emailService.sendEmail({
        to: 'your-email@example.com', // Change this
        subject: 'Test Email - Kandidatentekort.nl',
        html: '<h1>Test Email</h1><p>This is a test email from kandidatentekort.nl</p>',
        text: 'Test Email - This is a test email from kandidatentekort.nl'
    });

    console.log('Send result:', result);
}

testResendSetup();
```

## 6. Production Checklist

- [ ] API key stored securely in environment variables
- [ ] DNS records added and verified
- [ ] Domain verified in Resend dashboard
- [ ] Test email sent successfully
- [ ] Email templates created and tested
- [ ] Error handling implemented
- [ ] Retry logic configured
- [ ] Monitoring set up (Resend dashboard)
- [ ] DMARC policy configured
- [ ] Sender addresses whitelisted

## 7. Best Practices

1. **Sender Reputation**
   - Use consistent from addresses
   - Implement proper unsubscribe links
   - Monitor bounce rates

2. **Security**
   - Never commit API keys
   - Use environment variables
   - Implement rate limiting

3. **Compliance**
   - Include unsubscribe links
   - Add company details in footer
   - Respect GDPR requirements

4. **Monitoring**
   - Check Resend dashboard regularly
   - Monitor delivery rates
   - Handle bounces and complaints

## 8. Troubleshooting

### Domain Not Verifying
- Check DNS propagation: https://dnschecker.org/
- Ensure no typos in DNS records
- Wait up to 48 hours for full propagation

### Emails Not Sending
- Check API key is correct
- Verify domain is verified
- Check Resend dashboard for errors
- Ensure from address uses verified domain

### Rate Limits
- Free tier: 100 emails/day
- Pro tier: 50,000 emails/month
- Implement proper queuing for bulk sends

## Support

- Resend Documentation: https://resend.com/docs
- Resend Status: https://status.resend.com/
- Support: support@resend.com
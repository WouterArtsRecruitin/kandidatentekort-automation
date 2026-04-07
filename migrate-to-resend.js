#!/usr/bin/env node
/**
 * 🔄 GMAIL TO RESEND MIGRATION SCRIPT
 * ===================================
 * Helps migrate from Gmail SMTP to Resend email service
 * 
 * Author: Recruitin B.V.
 * Date: December 2024
 */

require('dotenv').config();
const fs = require('fs');
const path = require('path');

console.log('🔄 Starting migration from Gmail SMTP to Resend...\n');

// Check current configuration
function checkCurrentConfig() {
    console.log('📋 Current Configuration:');
    console.log('------------------------');
    
    // Check Gmail config
    if (process.env.GMAIL_USER || process.env.GMAIL_APP_PASSWORD) {
        console.log('⚠️  Gmail SMTP configured:');
        console.log(`   - User: ${process.env.GMAIL_USER || 'Not set'}`);
        console.log(`   - Password: ${process.env.GMAIL_APP_PASSWORD ? '***set***' : 'Not set'}`);
    }
    
    // Check Resend config
    if (process.env.RESEND_API_KEY) {
        console.log('✅ Resend already configured:');
        console.log(`   - API Key: ${process.env.RESEND_API_KEY.substring(0, 10)}...`);
        console.log(`   - From Email: ${process.env.RESEND_FROM_EMAIL || 'Not set'}`);
    } else {
        console.log('❌ Resend not configured yet');
    }
    
    console.log('\n');
}

// Migration steps
function showMigrationSteps() {
    console.log('📝 Migration Steps:');
    console.log('==================\n');
    
    const steps = [
        {
            title: '1. Create Resend Account',
            tasks: [
                'Go to https://resend.com/signup',
                'Sign up with your work email',
                'Verify your email address'
            ]
        },
        {
            title: '2. Add kandidatentekort.nl Domain',
            tasks: [
                'Go to https://resend.com/domains',
                'Click "Add Domain"',
                'Enter: kandidatentekort.nl',
                'Select region: Europe (eu-west-1)'
            ]
        },
        {
            title: '3. Configure DNS Records',
            tasks: [
                'Add SPF record: "v=spf1 include:amazonses.com ~all"',
                'Add 3 DKIM CNAME records provided by Resend',
                'Optional: Add DMARC record for better deliverability',
                'Wait 5-10 minutes for DNS propagation'
            ]
        },
        {
            title: '4. Get API Key',
            tasks: [
                'Go to https://resend.com/api-keys',
                'Create new API key named "kandidatentekort-production"',
                'Copy the API key (starts with re_)'
            ]
        },
        {
            title: '5. Update Environment Variables',
            tasks: [
                'Add RESEND_API_KEY=re_your_api_key',
                'Add RESEND_FROM_EMAIL=noreply@kandidatentekort.nl',
                'Comment out or remove GMAIL_USER and GMAIL_APP_PASSWORD'
            ]
        },
        {
            title: '6. Update Code',
            tasks: [
                'Replace nodemailer/Gmail code with EmailService',
                'Update email sending logic to use new service',
                'Test email functionality'
            ]
        }
    ];
    
    steps.forEach((step, index) => {
        console.log(`\n${step.title}`);
        console.log('-'.repeat(step.title.length));
        step.tasks.forEach(task => {
            console.log(`  ✓ ${task}`);
        });
    });
    
    console.log('\n');
}

// Code migration examples
function showCodeMigration() {
    console.log('💻 Code Migration Examples:');
    console.log('==========================\n');
    
    console.log('❌ OLD Gmail/Nodemailer Code:');
    console.log('```javascript');
    console.log(`const nodemailer = require('nodemailer');

const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
        user: process.env.GMAIL_USER,
        pass: process.env.GMAIL_APP_PASSWORD
    }
});

await transporter.sendMail({
    from: process.env.GMAIL_USER,
    to: 'recipient@example.com',
    subject: 'Test Email',
    html: '<h1>Hello</h1>'
});`);
    console.log('```\n');
    
    console.log('✅ NEW Resend Code:');
    console.log('```javascript');
    console.log(`const EmailService = require('./email-service');

const emailService = new EmailService(process.env.RESEND_API_KEY, {
    defaultFrom: process.env.RESEND_FROM_EMAIL
});

await emailService.sendEmail({
    to: 'recipient@example.com',
    subject: 'Test Email',
    html: '<h1>Hello</h1>'
});`);
    console.log('```\n');
}

// Environment file updater
function updateEnvFile() {
    const envPath = path.join(__dirname, '.env');
    if (!fs.existsSync(envPath)) {
        console.log('⚠️  No .env file found. Please create one from .env.example');
        return;
    }
    
    console.log('📝 Suggested .env updates:');
    console.log('=========================\n');
    console.log('Add these lines to your .env file:\n');
    console.log('# Resend Email Service');
    console.log('RESEND_API_KEY=re_YOUR_API_KEY_HERE');
    console.log('RESEND_FROM_EMAIL=noreply@kandidatentekort.nl');
    console.log('RESEND_FROM_NAME=Kandidatentekort\n');
    console.log('# Optional sender addresses');
    console.log('RESEND_REPORTS_EMAIL=rapporten@kandidatentekort.nl');
    console.log('RESEND_NOTIFICATIONS_EMAIL=notificaties@kandidatentekort.nl\n');
    console.log('Then comment out or remove:');
    console.log('# GMAIL_USER=...');
    console.log('# GMAIL_APP_PASSWORD=...\n');
}

// Test commands
function showTestCommands() {
    console.log('🧪 Test Commands:');
    console.log('=================\n');
    console.log('# Install dependencies');
    console.log('npm install\n');
    console.log('# Verify email setup');
    console.log('npm run verify:email\n');
    console.log('# Run email tests');
    console.log('npm run test:email\n');
}

// Main execution
function main() {
    console.log('╔════════════════════════════════════════════╗');
    console.log('║   Gmail → Resend Migration Assistant       ║');
    console.log('║   For kandidatentekort.nl                  ║');
    console.log('╚════════════════════════════════════════════╝\n');
    
    checkCurrentConfig();
    showMigrationSteps();
    showCodeMigration();
    updateEnvFile();
    showTestCommands();
    
    console.log('📚 Additional Resources:');
    console.log('=======================');
    console.log('- Setup Guide: ./RESEND-SETUP-GUIDE.md');
    console.log('- Email Service: ./email-service.js');
    console.log('- Integration Examples: ./email-integration-example.js');
    console.log('- Resend Docs: https://resend.com/docs\n');
    
    console.log('✨ Migration checklist saved to: migration-checklist.txt\n');
    
    // Save checklist
    const checklist = `Kandidatentekort.nl Email Migration Checklist
============================================

[ ] Create Resend account at https://resend.com/signup
[ ] Add kandidatentekort.nl domain in Resend dashboard
[ ] Configure DNS records (SPF, DKIM, DMARC)
[ ] Verify domain in Resend dashboard
[ ] Get API key from https://resend.com/api-keys
[ ] Update .env file with Resend credentials
[ ] Remove/comment Gmail SMTP credentials
[ ] Update code to use EmailService instead of nodemailer
[ ] Test email sending functionality
[ ] Monitor first few sends in Resend dashboard
[ ] Update any webhooks or integrations

Notes:
- DNS propagation can take up to 48 hours
- Keep Gmail credentials until migration is complete
- Test thoroughly before removing old code
`;
    
    fs.writeFileSync('migration-checklist.txt', checklist);
}

// Run migration assistant
if (require.main === module) {
    main();
}
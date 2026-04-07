#!/usr/bin/env node
/**
 * 🧪 RESEND SETUP TEST SCRIPT
 * ===========================
 * Comprehensive test script for Resend email configuration
 * 
 * Author: Recruitin B.V.
 * Date: December 2024
 */

require('dotenv').config();
const EmailService = require('./email-service');

// ANSI color codes for better output
const colors = {
    reset: '\x1b[0m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m'
};

// Helper functions
const log = {
    success: (msg) => console.log(`${colors.green}✅ ${msg}${colors.reset}`),
    error: (msg) => console.log(`${colors.red}❌ ${msg}${colors.reset}`),
    warning: (msg) => console.log(`${colors.yellow}⚠️  ${msg}${colors.reset}`),
    info: (msg) => console.log(`${colors.blue}ℹ️  ${msg}${colors.reset}`),
    test: (msg) => console.log(`${colors.cyan}🧪 ${msg}${colors.reset}`)
};

// Test configuration
const TEST_CONFIG = {
    testEmail: process.env.TEST_EMAIL || 'test@example.com',
    timeout: 30000 // 30 seconds
};

// Main test suite
async function runTests() {
    console.log('\n╔════════════════════════════════════════════╗');
    console.log('║     Resend Email Service Test Suite        ║');
    console.log('║         kandidatentekort.nl                ║');
    console.log('╚════════════════════════════════════════════╝\n');

    let emailService;
    let testResults = {
        passed: 0,
        failed: 0,
        warnings: 0
    };

    // Test 1: Environment Variables
    log.test('Testing environment variables...');
    if (!process.env.RESEND_API_KEY) {
        log.error('RESEND_API_KEY not found in environment variables');
        log.info('Please add RESEND_API_KEY to your .env file');
        return;
    } else {
        log.success('RESEND_API_KEY found');
        testResults.passed++;
    }

    if (!process.env.RESEND_FROM_EMAIL) {
        log.warning('RESEND_FROM_EMAIL not set, using default: noreply@kandidatentekort.nl');
        testResults.warnings++;
    } else {
        log.success(`RESEND_FROM_EMAIL set to: ${process.env.RESEND_FROM_EMAIL}`);
        testResults.passed++;
    }

    // Test 2: Initialize Email Service
    log.test('\nInitializing Email Service...');
    try {
        emailService = new EmailService(process.env.RESEND_API_KEY, {
            defaultFrom: process.env.RESEND_FROM_EMAIL || 'noreply@kandidatentekort.nl',
            maxRetries: 3
        });
        log.success('Email Service initialized successfully');
        testResults.passed++;
    } catch (error) {
        log.error(`Failed to initialize Email Service: ${error.message}`);
        testResults.failed++;
        return;
    }

    // Test 3: Domain Verification
    log.test('\nVerifying domain configuration...');
    try {
        const domainStatus = await emailService.verifyDomain();
        
        if (domainStatus.verified) {
            log.success('Domain kandidatentekort.nl is verified!');
            log.info(`Domain status: ${domainStatus.status}`);
            testResults.passed++;
        } else {
            log.error('Domain kandidatentekort.nl is NOT verified');
            
            if (domainStatus.records) {
                log.warning('Please add these DNS records:');
                console.log(JSON.stringify(domainStatus.records, null, 2));
            }
            
            log.info('Visit https://resend.com/domains to complete verification');
            testResults.failed++;
        }
    } catch (error) {
        log.error(`Domain verification error: ${error.message}`);
        testResults.failed++;
    }

    // Test 4: Send Test Email
    log.test('\nSending test email...');
    log.info(`Recipient: ${TEST_CONFIG.testEmail}`);
    
    try {
        const result = await emailService.sendEmail({
            to: TEST_CONFIG.testEmail,
            subject: 'Test Email - Kandidatentekort.nl Setup',
            html: `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #FF6B35; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
                        .content { background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }
                        .status { background-color: #10B981; color: white; padding: 10px; border-radius: 5px; text-align: center; margin: 20px 0; }
                        .details { background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
                        .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #666; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Resend Email Test</h1>
                        </div>
                        <div class="content">
                            <div class="status">
                                ✅ Email Configuration Working!
                            </div>
                            <p>This test email confirms that your Resend integration for <strong>kandidatentekort.nl</strong> is working correctly.</p>
                            
                            <div class="details">
                                <h3>Configuration Details:</h3>
                                <ul>
                                    <li><strong>Domain:</strong> kandidatentekort.nl</li>
                                    <li><strong>Service:</strong> Resend</li>
                                    <li><strong>Timestamp:</strong> ${new Date().toLocaleString('nl-NL')}</li>
                                    <li><strong>From:</strong> ${process.env.RESEND_FROM_EMAIL || 'noreply@kandidatentekort.nl'}</li>
                                </ul>
                            </div>
                            
                            <p>You can now start sending emails through your application!</p>
                        </div>
                        <div class="footer">
                            <p>Powered by Recruitin B.V. - kandidatentekort.nl</p>
                        </div>
                    </div>
                </body>
                </html>
            `,
            text: 'Test Email - Your Resend integration for kandidatentekort.nl is working correctly!'
        });

        if (result.success) {
            log.success(`Test email sent successfully!`);
            log.info(`Message ID: ${result.messageId}`);
            log.info('Check your inbox to confirm delivery');
            testResults.passed++;
        } else {
            log.error(`Failed to send test email: ${result.error}`);
            testResults.failed++;
        }
    } catch (error) {
        log.error(`Email send error: ${error.message}`);
        testResults.failed++;
    }

    // Test 5: Template Email
    log.test('\nTesting template email...');
    try {
        const templateResult = await emailService.sendTemplateEmail({
            to: TEST_CONFIG.testEmail,
            template: 'candidate-report',
            data: {
                recipientName: 'Test Recruiter',
                candidateName: 'Jan de Test',
                message: 'Dit is een test van het kandidaat rapport template.',
                reportLink: 'https://kandidatentekort.nl/test-report'
            }
        });

        if (templateResult.success) {
            log.success('Template email sent successfully!');
            testResults.passed++;
        } else {
            log.error(`Template email failed: ${templateResult.error}`);
            testResults.failed++;
        }
    } catch (error) {
        log.error(`Template email error: ${error.message}`);
        testResults.failed++;
    }

    // Test 6: Error Handling
    log.test('\nTesting error handling...');
    try {
        const errorResult = await emailService.sendEmail({
            to: 'invalid-email',
            subject: 'Error Test',
            html: '<p>This should fail</p>'
        });

        if (!errorResult.success) {
            log.success('Error handling working correctly');
            log.info(`Error caught: ${errorResult.error}`);
            testResults.passed++;
        } else {
            log.warning('Expected error but email was sent');
            testResults.warnings++;
        }
    } catch (error) {
        log.success('Error handling working correctly');
        testResults.passed++;
    }

    // Summary
    console.log('\n╔════════════════════════════════════════════╗');
    console.log('║              Test Summary                  ║');
    console.log('╚════════════════════════════════════════════╝\n');
    
    console.log(`${colors.green}Passed: ${testResults.passed}${colors.reset}`);
    console.log(`${colors.red}Failed: ${testResults.failed}${colors.reset}`);
    console.log(`${colors.yellow}Warnings: ${testResults.warnings}${colors.reset}`);
    
    if (testResults.failed === 0) {
        console.log(`\n${colors.green}🎉 All tests passed! Your Resend setup is ready.${colors.reset}`);
    } else {
        console.log(`\n${colors.red}⚠️  Some tests failed. Please check the errors above.${colors.reset}`);
    }

    // Next steps
    console.log('\n📝 Next Steps:');
    console.log('==============');
    if (testResults.failed > 0) {
        console.log('1. Fix the issues mentioned above');
        console.log('2. Verify DNS records if domain verification failed');
        console.log('3. Check API key permissions in Resend dashboard');
    } else {
        console.log('1. Update your application code to use EmailService');
        console.log('2. Remove old Gmail SMTP configuration');
        console.log('3. Monitor email delivery in Resend dashboard');
        console.log('4. Set up webhook for bounce/complaint handling (optional)');
    }
    
    console.log('\n📚 Resources:');
    console.log('- Resend Dashboard: https://resend.com/emails');
    console.log('- API Documentation: https://resend.com/docs');
    console.log('- Support: support@resend.com\n');
}

// Run tests
if (require.main === module) {
    runTests().catch(error => {
        console.error('Unexpected error:', error);
        process.exit(1);
    });
}
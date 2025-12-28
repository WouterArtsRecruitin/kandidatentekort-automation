/**
 * 📧 EMAIL INTEGRATION EXAMPLES
 * =============================
 * Examples of integrating Resend email service in your application
 * 
 * Author: Recruitin B.V.
 * Date: December 2024
 */

require('dotenv').config();
const EmailService = require('./email-service');

// Initialize email service
const emailService = new EmailService(process.env.RESEND_API_KEY, {
    defaultFrom: process.env.RESEND_FROM_EMAIL || 'noreply@kandidatentekort.nl',
    maxRetries: 3,
    retryDelay: 1000
});

/**
 * Example 1: Send candidate report
 */
async function sendCandidateReport(candidateData, recipientEmail) {
    try {
        const result = await emailService.sendTemplateEmail({
            to: recipientEmail,
            template: 'candidate-report',
            data: {
                recipientName: candidateData.recruiterName || 'Recruiter',
                candidateName: candidateData.name,
                message: `De assessment voor ${candidateData.name} is succesvol afgerond.`,
                reportLink: candidateData.reportUrl
            },
            tags: {
                type: 'candidate-report',
                candidateId: candidateData.id,
                source: 'kandidatentekort-automation'
            }
        });

        if (result.success) {
            console.log(`✅ Report sent to ${recipientEmail} (ID: ${result.messageId})`);
        } else {
            console.error(`❌ Failed to send report: ${result.error}`);
        }

        return result;
    } catch (error) {
        console.error('Error sending candidate report:', error);
        throw error;
    }
}

/**
 * Example 2: Send vacancy notification
 */
async function sendVacancyNotification(vacancy, candidates) {
    try {
        const emailPromises = candidates.map(candidate => 
            emailService.sendTemplateEmail({
                to: candidate.email,
                template: 'vacancy-notification',
                data: {
                    candidateName: candidate.name,
                    jobTitle: vacancy.title,
                    companyName: vacancy.company,
                    location: vacancy.location,
                    salary: vacancy.salary || 'Marktconform',
                    jobDescription: vacancy.description
                },
                tags: {
                    type: 'vacancy-notification',
                    vacancyId: vacancy.id,
                    candidateId: candidate.id
                }
            })
        );

        const results = await Promise.all(emailPromises);
        
        const successCount = results.filter(r => r.success).length;
        console.log(`✅ Sent ${successCount}/${candidates.length} vacancy notifications`);

        return results;
    } catch (error) {
        console.error('Error sending vacancy notifications:', error);
        throw error;
    }
}

/**
 * Example 3: Send custom HTML email
 */
async function sendCustomEmail(to, subject, htmlContent, attachments = []) {
    try {
        const result = await emailService.sendEmail({
            to: to,
            subject: subject,
            html: htmlContent,
            attachments: attachments,
            from: 'Kandidatentekort <info@kandidatentekort.nl>'
        });

        return result;
    } catch (error) {
        console.error('Error sending custom email:', error);
        throw error;
    }
}

/**
 * Example 4: Send email with attachments
 */
async function sendEmailWithAttachment(to, subject, message, pdfBuffer, filename) {
    try {
        const result = await emailService.sendEmail({
            to: to,
            subject: subject,
            html: `
                <h2>${subject}</h2>
                <p>${message}</p>
                <p>Zie bijlage voor meer details.</p>
                <p>Met vriendelijke groet,<br>Team Kandidatentekort</p>
            `,
            attachments: [{
                filename: filename,
                content: pdfBuffer.toString('base64'),
                contentType: 'application/pdf'
            }]
        });

        return result;
    } catch (error) {
        console.error('Error sending email with attachment:', error);
        throw error;
    }
}

/**
 * Example 5: Batch send with rate limiting
 */
async function sendBulkEmails(recipients, subject, template) {
    try {
        const emails = recipients.map(recipient => ({
            to: recipient.email,
            subject: subject,
            html: template.replace(/{{name}}/g, recipient.name),
            tags: {
                campaign: 'bulk-send',
                recipientId: recipient.id
            }
        }));

        const results = await emailService.sendBatch(emails);
        
        const summary = {
            total: results.length,
            successful: results.filter(r => r.success).length,
            failed: results.filter(r => !r.success).length
        };

        console.log('Bulk send summary:', summary);
        return summary;
    } catch (error) {
        console.error('Error in bulk send:', error);
        throw error;
    }
}

/**
 * Example 6: Integration with Zapier webhook
 */
async function handleZapierEmailRequest(req, res) {
    try {
        const { to, subject, template, data } = req.body;

        if (!to || !subject) {
            return res.status(400).json({
                error: 'Missing required fields: to, subject'
            });
        }

        let result;
        if (template) {
            // Use template
            result = await emailService.sendTemplateEmail({
                to,
                template,
                data
            });
        } else {
            // Send custom email
            result = await emailService.sendEmail({
                to,
                subject,
                html: data.html || data.body,
                text: data.text
            });
        }

        res.json({
            success: result.success,
            messageId: result.messageId,
            error: result.error
        });

    } catch (error) {
        console.error('Zapier email request error:', error);
        res.status(500).json({
            error: error.message
        });
    }
}

/**
 * Example 7: Verify setup and domain
 */
async function verifyEmailSetup() {
    try {
        console.log('🔍 Verifying Resend setup...\n');

        // Check domain status
        const domainStatus = await emailService.verifyDomain();
        
        if (domainStatus.verified) {
            console.log('✅ Domain kandidatentekort.nl is verified');
            console.log('📊 Domain details:', domainStatus.domain);
        } else {
            console.log('❌ Domain not verified');
            console.log('📋 Please add these DNS records:');
            console.log(JSON.stringify(domainStatus.records, null, 2));
        }

        // Send test email
        if (domainStatus.verified) {
            console.log('\n📧 Sending test email...');
            const testResult = await emailService.sendEmail({
                to: process.env.TEST_EMAIL || 'test@example.com',
                subject: 'Test Email - Resend Setup Complete',
                html: `
                    <h1>Resend Setup Successful!</h1>
                    <p>This test email confirms that your Resend integration is working correctly.</p>
                    <p>Domain: kandidatentekort.nl</p>
                    <p>Time: ${new Date().toISOString()}</p>
                `
            });

            if (testResult.success) {
                console.log('✅ Test email sent successfully!');
                console.log('📬 Message ID:', testResult.messageId);
            } else {
                console.log('❌ Test email failed:', testResult.error);
            }
        }

    } catch (error) {
        console.error('Setup verification error:', error);
    }
}

// Export functions for use in other modules
module.exports = {
    emailService,
    sendCandidateReport,
    sendVacancyNotification,
    sendCustomEmail,
    sendEmailWithAttachment,
    sendBulkEmails,
    handleZapierEmailRequest,
    verifyEmailSetup
};

// Run verification if this file is executed directly
if (require.main === module) {
    verifyEmailSetup();
}
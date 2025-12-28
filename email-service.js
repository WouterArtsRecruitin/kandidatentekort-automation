/**
 * 📧 RESEND EMAIL SERVICE
 * =======================
 * Professional email service for kandidatentekort.nl using Resend
 * 
 * Features:
 * - Resend API integration
 * - Domain verification for kandidatentekort.nl
 * - Retry logic with exponential backoff
 * - Template support
 * - Error handling & logging
 * 
 * Author: Recruitin B.V.
 * Date: December 2024
 */

const { Resend } = require('resend');

class EmailService {
    constructor(apiKey, options = {}) {
        if (!apiKey) {
            throw new Error('Resend API key is required');
        }

        this.resend = new Resend(apiKey);
        this.defaultFrom = options.defaultFrom || 'noreply@kandidatentekort.nl';
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000; // ms
        this.isDevelopment = process.env.NODE_ENV === 'development';
    }

    /**
     * Send email with retry logic
     * @param {Object} options - Email options
     * @param {string} options.to - Recipient email
     * @param {string} options.subject - Email subject
     * @param {string} options.html - HTML content
     * @param {string} options.text - Plain text content (optional)
     * @param {string} options.from - Sender email (optional)
     * @param {string[]} options.cc - CC recipients (optional)
     * @param {string[]} options.bcc - BCC recipients (optional)
     * @param {Object[]} options.attachments - File attachments (optional)
     * @param {Object} options.tags - Email tags for tracking (optional)
     * @returns {Promise<Object>} Send result
     */
    async sendEmail(options) {
        const emailData = {
            from: options.from || this.defaultFrom,
            to: Array.isArray(options.to) ? options.to : [options.to],
            subject: options.subject,
            html: options.html,
            text: options.text,
            cc: options.cc,
            bcc: options.bcc,
            attachments: options.attachments,
            tags: options.tags
        };

        // Log in development mode
        if (this.isDevelopment) {
            console.log('📧 Sending email:', {
                to: emailData.to,
                subject: emailData.subject,
                from: emailData.from
            });
        }

        // Retry logic with exponential backoff
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                const result = await this.resend.emails.send(emailData);

                if (this.isDevelopment) {
                    console.log('✅ Email sent successfully:', result.id);
                }

                return {
                    success: true,
                    messageId: result.id,
                    data: result
                };

            } catch (error) {
                console.error(`❌ Email send attempt ${attempt} failed:`, error.message);

                if (attempt === this.maxRetries) {
                    return {
                        success: false,
                        error: error.message,
                        attempts: attempt
                    };
                }

                // Exponential backoff
                const delay = this.retryDelay * Math.pow(2, attempt - 1);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    /**
     * Send email using template
     * @param {Object} options - Template email options
     * @param {string} options.to - Recipient email
     * @param {string} options.template - Template name
     * @param {Object} options.data - Template variables
     * @returns {Promise<Object>} Send result
     */
    async sendTemplateEmail(options) {
        const templates = {
            'candidate-report': {
                subject: 'Uw kandidatenprofiel rapport - {{candidateName}}',
                html: `
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <style>
                            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                            .header { background-color: #FF6B35; color: white; padding: 20px; text-align: center; }
                            .content { padding: 20px; }
                            .footer { background-color: #f4f4f4; padding: 20px; text-align: center; font-size: 12px; }
                            .button { display: inline-block; padding: 10px 20px; background-color: #FF6B35; color: white; text-decoration: none; border-radius: 5px; }
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h1>Kandidatentekort.nl</h1>
                        </div>
                        <div class="content">
                            <h2>Beste {{recipientName}},</h2>
                            <p>Hierbij ontvangt u het rapport voor kandidaat: <strong>{{candidateName}}</strong></p>
                            <p>{{message}}</p>
                            <p><a href="{{reportLink}}" class="button">Bekijk Rapport</a></p>
                        </div>
                        <div class="footer">
                            <p>&copy; 2024 Kandidatentekort.nl - Powered by Recruitin B.V.</p>
                        </div>
                    </body>
                    </html>
                `
            },
            'vacancy-notification': {
                subject: 'Nieuwe vacature match - {{jobTitle}}',
                html: `
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <style>
                            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                            .header { background-color: #1E3A8A; color: white; padding: 20px; text-align: center; }
                            .content { padding: 20px; }
                            .job-details { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }
                            .footer { background-color: #f4f4f4; padding: 20px; text-align: center; font-size: 12px; }
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h1>Nieuwe Vacature Match</h1>
                        </div>
                        <div class="content">
                            <h2>Beste {{candidateName}},</h2>
                            <p>We hebben een interessante vacature gevonden die aansluit bij uw profiel:</p>
                            <div class="job-details">
                                <h3>{{jobTitle}}</h3>
                                <p><strong>Bedrijf:</strong> {{companyName}}</p>
                                <p><strong>Locatie:</strong> {{location}}</p>
                                <p><strong>Salaris:</strong> {{salary}}</p>
                                <p>{{jobDescription}}</p>
                            </div>
                            <p>Heeft u interesse? Neem contact met ons op!</p>
                        </div>
                        <div class="footer">
                            <p>&copy; 2024 Kandidatentekort.nl - Uw partner in recruitment</p>
                        </div>
                    </body>
                    </html>
                `
            }
        };

        const template = templates[options.template];
        if (!template) {
            throw new Error(`Template '${options.template}' not found`);
        }

        // Replace variables in template
        let html = template.html;
        let subject = template.subject;

        Object.entries(options.data || {}).forEach(([key, value]) => {
            const regex = new RegExp(`{{${key}}}`, 'g');
            html = html.replace(regex, value);
            subject = subject.replace(regex, value);
        });

        return this.sendEmail({
            to: options.to,
            subject: subject,
            html: html,
            from: options.from,
            tags: options.tags
        });
    }

    /**
     * Send batch emails
     * @param {Array<Object>} emails - Array of email options
     * @returns {Promise<Array<Object>>} Array of send results
     */
    async sendBatch(emails) {
        const results = [];
        
        // Process in chunks to avoid rate limits
        const chunkSize = 10;
        for (let i = 0; i < emails.length; i += chunkSize) {
            const chunk = emails.slice(i, i + chunkSize);
            const chunkResults = await Promise.all(
                chunk.map(email => this.sendEmail(email))
            );
            results.push(...chunkResults);
            
            // Small delay between chunks
            if (i + chunkSize < emails.length) {
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        }

        return results;
    }

    /**
     * Verify domain configuration
     * @returns {Promise<Object>} Domain verification status
     */
    async verifyDomain() {
        try {
            const domains = await this.resend.domains.list();
            const kandidatenDomain = domains.data?.find(d => 
                d.name === 'kandidatentekort.nl'
            );

            if (!kandidatenDomain) {
                return {
                    verified: false,
                    message: 'Domain kandidatentekort.nl not found in Resend account'
                };
            }

            return {
                verified: kandidatenDomain.status === 'verified',
                status: kandidatenDomain.status,
                records: kandidatenDomain.records,
                domain: kandidatenDomain
            };

        } catch (error) {
            return {
                verified: false,
                error: error.message
            };
        }
    }
}

module.exports = EmailService;
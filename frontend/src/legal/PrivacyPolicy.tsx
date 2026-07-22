import type { ReactNode } from 'react'

const LAST_UPDATED = 'July 22, 2026'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-gray-400">{children}</div>
    </section>
  )
}

export function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
        <header className="mb-10 space-y-2 border-b border-gray-800 pb-6">
          <h1 className="text-2xl font-semibold sm:text-3xl">ValetQ Privacy Policy</h1>
          <p className="text-sm text-gray-500">Last Updated: {LAST_UPDATED}</p>
        </header>

        <div className="space-y-10">
          <Section title="1. What ValetQ Is">
            <p>
              ValetQ is a valet parking management platform used by restaurants, hotels, and other venues
              ("Venues") to coordinate valet parking requests. Guests interact with the valet service over
              WhatsApp — scanning a key tag to request parking, and receiving status updates as their vehicle
              is parked and retrieved. Venue staff use a web dashboard to manage these requests. This policy
              describes what information ValetQ processes as part of that service, and why.
            </p>
          </Section>

          <Section title="2. Information We Process">
            <p>To operate the valet service, ValetQ processes the following categories of information:</p>
            <ul className="list-disc space-y-2 pl-5">
              <li>
                <span className="text-gray-300">WhatsApp phone numbers.</span> The phone number a guest
                messages from, and the phone numbers of Venue staff (used both to receive WhatsApp
                notifications and to sign in to the staff dashboard).
              </li>
              <li>
                <span className="text-gray-300">WhatsApp messages related to the valet service.</span>{' '}
                Inbound messages guests or staff send to initiate, check on, or respond to a valet request
                (for example, a key-tag scan message or a reply confirming a job), and the outbound status
                messages ValetQ sends in response.
              </li>
              <li>
                <span className="text-gray-300">Vehicle and session information.</span> The vehicle
                registration number captured by valet staff when a car is parked, and the state of each
                valet session (requested, accepted, parked, retrieving, ready, completed, or cancelled).
              </li>
              <li>
                <span className="text-gray-300">Venue information.</span> The name (and, where provided,
                address) of the Venue a session belongs to, and which staff accounts have access to it.
              </li>
              <li>
                <span className="text-gray-300">Timestamps and operational/audit logs.</span> The time each
                valet session was created and each time it changed state, along with which staff account (if
                any) performed that action — kept as an audit trail of the service being provided.
              </li>
            </ul>
          </Section>

          <Section title="3. Why We Process This Information">
            <p>This information is processed to:</p>
            <ul className="list-disc space-y-2 pl-5">
              <li>Create and route valet parking requests between guests and Venue staff.</li>
              <li>Send guests WhatsApp updates about the status of their vehicle.</li>
              <li>Let Venue staff sign in, manage requests, and coordinate valet operations for their venue.</li>
              <li>
                Maintain an accurate record of what happened during a session, for accountability and to
                resolve disputes or issues a Venue or guest may raise.
              </li>
              <li>Operate, maintain, and improve the reliability of the ValetQ service itself.</li>
            </ul>
          </Section>

          <Section title="4. Meta / WhatsApp Integration">
            <p>
              ValetQ sends and receives WhatsApp messages through Meta's WhatsApp Cloud API — we do not use a
              third-party messaging intermediary. When a guest or staff member messages ValetQ's WhatsApp
              number, that message is delivered to us via Meta's platform, and our replies are sent back the
              same way.
            </p>
            <p>
              Meta processes WhatsApp messages sent and received through this integration in accordance with
              its own terms and privacy policy, which governs Meta's handling of that data as the operator of
              the WhatsApp platform, independent of ValetQ. We encourage you to review Meta's WhatsApp privacy
              policy for details on how Meta itself handles this data.
            </p>
          </Section>

          <Section title="5. Data Sharing and Service Providers">
            <p>
              We do not share personal information with third parties except where necessary to operate
              ValetQ, or where required by law. The service providers we currently use to run ValetQ include:
            </p>
            <ul className="list-disc space-y-2 pl-5">
              <li>Meta, for sending and receiving WhatsApp messages via the WhatsApp Cloud API.</li>
              <li>Our database and authentication provider, for storing account and session data securely.</li>
              <li>Our hosting providers, for running the ValetQ backend and web application.</li>
            </ul>
            <p>
              These providers process information only as needed to provide their respective service to
              ValetQ, and are not permitted to use it for their own independent purposes.
            </p>
          </Section>

          <Section title="6. Data Retention">
            <p>
              We retain guest, session, and audit information for as long as needed to provide the valet
              service and to maintain a usable operational record for the Venue (for example, so a Venue can
              look back at past sessions). We have not adopted a fixed automatic deletion schedule at this
              time. If you request deletion of your information as described in Section 9, we will act on
              that request as described there.
            </p>
          </Section>

          <Section title="7. Security">
            <p>
              We take reasonable steps to protect the information ValetQ processes, including restricting
              access to Venue staff based on their role and the Venues they are granted access to, and serving
              the ValetQ web application and API over HTTPS. We have not obtained any third-party security
              certification, and no security measure can guarantee complete protection against unauthorized
              access, loss, or misuse.
            </p>
          </Section>

          <Section title="8. No Selling of Personal Information">
            <p>We do not sell personal information to anyone, for any purpose.</p>
          </Section>

          <Section title="9. Data Deletion and Your Rights">
            <p>
              If you are a guest or Venue staff member and would like to request access to, correction of, or
              deletion of your personal information held by ValetQ, contact us using the details in Section
              11. We will respond to your request and, where deletion is appropriate and not in conflict with
              a Venue's legitimate operational or record-keeping needs, remove or anonymize the information
              identified in your request.
            </p>
          </Section>

          <Section title="10. Changes to This Policy">
            <p>
              We may update this Privacy Policy from time to time as ValetQ evolves. If we make changes,
              we will update the "Last Updated" date at the top of this page. We encourage you to review this
              page periodically.
            </p>
          </Section>

          <Section title="11. Contact Us">
            <p>
              If you have questions about this Privacy Policy or how ValetQ processes your information,
              contact us at{' '}
              <a href="mailto:sreeman.ambati@valetq.com" className="text-indigo-400 hover:text-indigo-300">
                sreeman.ambati@valetq.com
              </a>
              .
            </p>
          </Section>
        </div>
      </div>
    </div>
  )
}

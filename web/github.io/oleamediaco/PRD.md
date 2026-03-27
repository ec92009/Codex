# Olea Media Co Website PRD

## Document Status

- Status: Draft
- Product: Olea Media Co website
- Platform: Static marketing site on GitHub Pages, with a future path to production CMS or custom site
- Current preview: `https://ec92009.github.io/Codex/oleamediaco/`
- Local workspace: `~/Codex/web/github.io/oleamediaco`

## 1. Product Summary

Olea Media Co needs a website that explains its visual listing upgrade services for real-estate agents and agencies in the Malaga-Marbella corridor. The site should make the offer easy to understand, show the difference between service levels, build trust quickly, and convert interested visitors into email or callback inquiries.

The current website exists as a concept gallery plus multiple design variants. This PRD defines the requirements for turning those concepts into one production-ready marketing site.

## 2. Problem

Real-estate agents often publish listings with weak visuals: dark photos, poor composition, unappealing empty rooms, or inconsistent presentation. That reduces buyer attention and lowers inquiry quality.

Olea Media Co solves this with a staged service model, but the current site is still positioned as a draft/concept experience rather than a focused commercial website. Visitors need a simpler path from first impression to understanding the offer to making contact.

## 3. Goals

- Explain the 4-stage service model clearly in under 60 seconds.
- Help agents quickly identify which service level fits a listing.
- Build credibility through visuals, positioning, and clear process explanation.
- Drive qualified leads via email, callback request, or future booking/contact form.
- Support multilingual presentation for English, Spanish, and French audiences.

## 4. Non-Goals

- Full booking and payment flow at launch.
- Customer account area or asset delivery portal.
- Dynamic quote generator.
- Blog, SEO content hub, or long-form editorial system in the first release.
- Lead scoring or CRM automation beyond simple inquiry capture.

## 5. Target Users

### Primary users

- Independent real-estate agents in the Malaga-Marbella corridor
- Boutique agencies managing mid- to high-value listings
- Agents with underperforming listings who need faster visual improvement

### Secondary users

- Agency owners evaluating a repeatable visual services partner
- Property marketers or listing coordinators
- Potential referral partners

## 6. User Needs

- Understand what Olea Media Co does immediately
- See before/after proof of value
- Understand the difference between Stage 1, 2, 3, and 4
- Know starting prices and what affects final pricing
- Understand the workflow, timing, and next steps
- Contact Olea Media Co without friction
- Read the site in their preferred language

## 7. Value Proposition

Olea Media Co helps agents improve weak listings with a flexible 4-stage service model, from photo cleanup to physical staging and final photography, so they can improve listing presentation without overcommitting to a one-size-fits-all package.

## 8. Success Metrics

### Primary metrics

- Inquiry conversion rate from site visit to contact action
- Click-through rate on primary CTA
- Percentage of visitors who reach pricing or service stages
- Number of qualified inbound leads per month

### Secondary metrics

- Engagement with before/after comparison modules
- Language switch usage
- PDF open/download rate
- Time on page for hero + pricing + CTA sections

## 9. Core Messaging

### Positioning statement

Olea Media Co improves real-estate listing performance with staged visual upgrade services tailored to the listing's needs and budget.

### Key messages

- Better visuals improve listing performance and first impressions
- Agents can choose the right service level instead of buying a full package every time
- Olea Media Co works across the Malaga-Marbella corridor
- The process is simple, fast, and designed for listing-ready delivery

### Trust signals to include

- Before/after comparison imagery
- Clear service stages
- Geographic focus
- Transparent starting prices
- Process clarity
- Future testimonials, client logos, or pilot case studies once available

## 10. Product Requirements

### 10.1 Information architecture

The production site should include these sections in this order:

1. Hero
2. Problem / value explanation
3. 4-stage service model
4. Pricing
5. Process
6. Trust / proof section
7. CTA / contact section

Optional secondary content:

- FAQ
- Downloadable offer sheet links
- Language switcher

### 10.2 Hero requirements

- Strong headline explaining the outcome for agents
- Short supporting paragraph
- Primary CTA
- Secondary CTA
- Immediate visual proof using before/after comparison
- Visible geographic positioning

### 10.3 Service model requirements

- Show all 4 stages clearly
- Explain who each stage is for
- Communicate differences in effort, output, and impact
- Allow scanning without long paragraphs

### 10.4 Pricing requirements

- Display starting prices for each stage
- Clarify that scope varies based on listing needs
- Avoid implying fixed pricing where scope is variable

### 10.5 Process requirements

- Show a simple 4-step workflow
- Make timing and expectations easy to understand
- Reduce friction for first-time agency visitors

### 10.6 Contact / conversion requirements

- Primary conversion path: email inquiry
- Secondary conversion path: callback request
- Future-ready space for form or scheduling embed
- CTA copy should be direct and service-oriented

### 10.7 Language requirements

- English, Spanish, and French support
- Language switch available in the top-level navigation area
- Core sales sections fully translated
- No partially translated production sections at launch

### 10.8 Visual / brand requirements

- Premium but practical presentation
- Strong editorial emphasis on imagery
- Avoid generic SaaS styling
- Clear hierarchy between concept navigation and actual customer-facing content
- Mobile experience must preserve readability and CTA access

## 11. Functional Requirements

- Static site must load reliably on GitHub Pages
- All internal navigation links must work
- Variant gallery must link correctly to each design variant
- Theme toggle should persist state locally
- Language toggle should switch translated content correctly
- Before/after sliders must work on desktop and mobile
- PDF links must remain valid

## 12. Content Requirements

- Final headline and subhead
- Final wording for each service stage
- Final starting prices and pricing notes
- CTA copy for email / callback
- Corridor/service area wording
- Draft proof elements until real testimonials or case studies exist

Open content dependencies:

- Real client examples or pilot case study
- Final contact details
- Final proof points and guarantees, if any
- Final brand copy in Spanish and French

## 13. MVP Scope

### In scope for MVP

- One production-ready homepage
- Before/after comparison module
- 4-stage service explanation
- Pricing section
- Process section
- CTA/contact section
- Multilingual support
- PDF links

### Out of scope for MVP

- Separate service detail pages
- Agency case study pages
- Booking integration
- CMS editing workflow
- Analytics dashboard UI

## 14. Risks

- Too many concept-gallery elements may dilute the core sales flow
- Placeholder copy may reduce trust if not replaced before public promotion
- Missing proof assets may weaken conversion even if layout is strong
- Multiple languages increase QA complexity
- Static-site implementation may become hard to maintain if copy diverges across variants

## 15. Assumptions

- The production website will consolidate into one primary direction rather than keep multiple equal variants
- Lead capture at launch can be handled via email or a simple form
- GitHub Pages remains acceptable for preview and possibly early public use
- The current 4-stage service model remains the core offer structure

## 16. Recommended Next Steps

1. Choose one visual direction as the production baseline.
2. Replace all remaining draft and concept language with final client-facing copy.
3. Add at least one real proof asset: case study, testimonial, or pilot result.
4. Define the final conversion path: email only, form, or booking.
5. Cut the concept-gallery framing from the public-facing production page.

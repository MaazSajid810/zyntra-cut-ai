# Kixy reference analysis for ZyntraCut AI

Reviewed 26 October 2026. This is a public-product assessment, not an audit of Kixy's private source code or processing quality. No account, purchase, uploaded video or processing job was submitted. The application code and existing user data were not changed.

## Findings and evidence limits

### Follow-up: four application routes

The user subsequently supplied authenticated screenshots. They establish the following visible structure, superseding the earlier unknown-layout assessment: Create has source import, tool shortcuts, usage cards, recent projects and discovery previews; Explore has category chips, source metadata and Get clips; Wizard has chat/new-chat, reusable prompts and editing suggestions; Studio has Video/Image modes, prompt/style/duration/quality, an advertised caption-removal tool and galleries. Screenshots of an unpaid state do not establish executed paid-job quality. Their 10 GB/600-minute/4K claims are not adopted as ZyntraCut limits.

The user explicitly chose free/local tools. Independent routes now implement Create, Explore, a local command Wizard and local design/photo-motion Studio, while preserving the full editor. These are not a general chat model or photorealistic scene generator. See PLATFORM_UPGRADE.md and the latest VALIDATION.md entry. No Kixy account, service or creator assets are integrated.

The user subsequently supplied authenticated screenshots. They establish the following visible structure (superseding the earlier unknown-layout assessment below): Create has a source-import hero, tool shortcuts, usage cards, recent projects and discovery previews; Explore has category chips, source thumbnails/metadata and Get clips; Wizard has chat/new-chat, reusable prompts and clip-editing suggestions; Studio has Video/Image modes, prompt/style/duration/quality controls, an advertised caption-removal tool and style galleries. The screenshots show the user's unpaid state, so they do not establish the quality or behavior of an executed paid job. Their advertised 10 GB/600-minute/4K limits are not adopted as ZyntraCut's limits.

The user explicitly chose free/local tools. The independent implementation now has real `/dashboard`, `/explore`, `/wizard`, `/studio` and `/editor` routes. Its local Wizard exposes supported reviewable commands, and Studio implements real title-image/photo-motion rendering. It does not pretend to synthesize new photorealistic scenes or use a general chat model. See `PLATFORM_UPGRADE.md` and the newest `VALIDATION.md` entry for implementation evidence and limits. No Kixy account, provider or assets are integrated.

On 26 October 2026, each URL supplied by the user was opened directly in a fresh Microsoft Edge context. All four ended on Kixy's sign-in page:

| Requested path | Observed destination |
|---|---|
| `/explore` | `/sign-in?next=%2Fexplore` |
| `/dashboard` | `/sign-in?next=%2Fdashboard` |
| `/wizard` | `/sign-in?next=%2Fwizard` |
| `/studio` | `/sign-in?next=%2Fstudio` |

Public captures and body text are saved under `artifacts/kixy-analysis/{route}-public.*`. An initial HTTP 200 was not evidence that an application screen was accessible: the loaded browser redirected to sign-in. None of the four private interfaces, menus or editing flows has been inspected. Their names alone cannot establish their feature sets. Screenshots or a screen recording from the user's authorized session are needed for a faithful screen-by-screen specification; passwords, cookies and tokens are not needed.

The user has clarified that the target is the complete application across these modules, rather than only its landing page or a basic clipping workflow. The current ZyntraCut source has a single `app/page.tsx` with state-based navigation, plus reusable import, library, review and editor components. A future multi-page structure can reuse those working components and APIs. The purpose of Kixy's Explore, Wizard and Studio must be verified before mapping them to clip discovery, onboarding or generation: those mappings are currently hypotheses, not observed features. No speculative routes or placeholder AI tools were implemented during this follow-up.

The public [homepage](https://kixy.ai/) presents link/file input, automatic highlight extraction, vertical captioned outputs and manual download/posting. It describes around ten candidates and a configurable upper limit. Demo cards show scores such as 9.6, platform labels and different framings. These are promotional examples, not results of our test. Precise scoring methods, cross-user uniqueness and actual processing accuracy remain unknown.

The most useful architecture disclosure is in Kixy's [privacy policy](https://kixy.ai/privacy): Vizard processes submitted videos and produces clips; Vercel hosts the app; Neon hosts the database. It also names Dodo Payments, Google, Resend, PostHog and Sentry, plus an unnamed storage provider. This supports the inference that clipping is at least partly outsourced. It does not establish Kixy's programming language, frontend framework, internal orchestration, model names or division of processing between Kixy and its provider.

The [sign-in page](https://kixy.ai/sign-in) offers Google and passwordless email. We did not inspect a functioning authenticated editor. Exact timeline capabilities, controls, file limits, duration bounds, export resolution, mobile-editor quality, import reliability and completion latency are unverified. No claim of comprehensive end-to-end competitor testing is made.

## Visual and interaction observations

Direct Edge captures are in `artifacts/kixy-analysis/desktop.png`, `mobile.png` and `results-demo.png`.

Observed design: white background, near-black text/buttons, a small yellow/black brand mark, generous whitespace, rounded input and upload controls. A large dark demonstration section uses blue glow behind portrait clip cards. The primary action appears immediately, ahead of feature explanations. The header is sparse; sign-in actions remain visible on mobile.

Measured landing-page typography: desktop H1 112px, weight 500, line-height 107.52px; mobile H1 56px. Computed font family begins with Inter Tight. At the tested 390px mobile viewport, document width was also 390px. This is one landing-page width check, not validation of every page, viewport or editor state.

The input and Get clips action share a rounded desktop row. On mobile, Upload occupies a separate full-width row. The demonstration explains progression with three steps before showing short-form cards. This is effective because the desired outcome is visible before users learn advanced editing controls.

Do not treat the public examples, ready indicator or sample scores as live processing. ZyntraCut should display actual jobs/results and label any illustrative example explicitly. Do not import Kixy's logo, creator sample media, copy or proprietary assets into our product.

## Additional published capabilities

The [connector page](https://kixy.ai/connect) advertises authenticated MCP-based clipping, job inspection, hook/flow/value grading, caption selection, trimming and MP4 export. It also describes idea-to-video styles, image/coloring-book generation and burned-caption removal for videos up to 60 seconds. These are published claims, not features exercised in this assessment. They are separate product modules; matching the clipping workflow does not require building all of them first. Burned-caption removal must not be confused with hiding a separate subtitle track or placing a cover over pixels.

The [plans page](https://kixy.ai/paywall) currently displays monthly Starter/Pro/Creator pricing of $24/$49/$139, or annual effective monthly prices of $9/$19/$49, with 200/500/1,000 monthly credits. It lists watermark-free output, up to ten clips and animated captions in 50+ languages. Registration alone is not free processing. These current pages differ from older search snippets.

There is also a published-policy inconsistency: the plans/support pages describe 20 credits for 30 source minutes and 38 for an hour, while the [terms](https://kixy.ai/terms) describe one credit per source minute. Support says monthly credits expire at renewal; terms describe rollover. Billing should be confirmed in actual checkout before relying on either description. No purchase was attempted. The terms make no promise of views or earnings.

## Comparison with the actual ZyntraCut implementation

| Area | ZyntraCut today | Gap or action |
|---|---|---|
| Beginner flow | Import, real processing status, preview gallery, explicit editor, manual export | Make the first screen quieter; put the two core choices directly below input |
| Count and duration | Custom 1-100 or Auto; 3-180-second source-duration ranges in import and generation | Preserve these requested controls; count remains a maximum |
| Selection | Source transcript heuristics plus measured audio energy, silence and sampled visual changes | Deeper semantic interpretation and representative real-footage evaluation |
| Framing | Ratios and existing crop/layout controls | Moving subject/speaker tracking and tested scene-dependent layouts |
| Captions | Editable transcript, animated styles, Urdu/Hindi/Roman Urdu and translation | Improve real speech alignment and recognition quality with reviewed samples |
| Preview/edit/export | Actual FFmpeg renders, visual trim/layer timing, Undo/Redo, MP4s | Faster preview proxies and eventually arbitrary multi-source timeline composition |
| Branding/audio/layers | Opt-in watermark/logo, text/stickers, effects, music, photos and B-roll | Contextual automation remains distinct from manual support |
| Privacy/deletion | Private guest workspace and individual/bulk/project deletion | Keep no-login preference; deployment still needs durable private storage and job infrastructure |
| Conversational tools | No ZyntraCut MCP connector | Optional later feature, not part of current functionality |
| New AI videos/caption erasure | Not implemented; existing caption covers do not erase footage | Separate model, cost, processing and quality evaluation required |

The comparison uses the existing implementation and validation reports. No new ZyntraCut processing benchmark was run for this analysis. Earlier tests demonstrate tested workflows, not parity with Kixy's unknown output quality.

## Proposed ZyntraCut product specification

1. **Create:** original branding, one prominent link field, Upload, custom count/Auto and duration range. Put language/style/quality behind optional customization. Preserve a compact mobile layout and the user's current preferences rather than automatically adopting Kixy's account/paywall.
2. **Processing:** actual download/transcription/analysis/render stages, completed/total previews, readable errors and safe retry. Show percentages only when the backend has a real denominator. Do not animate fabricated completion estimates.
3. **Results:** ready clips first, actual preview player, source timestamps, duration, score explanation, edit/download/delete and existing selection/bulk actions. Keep source posters labelled until clip-specific thumbnails are generated. Never download automatically.
4. **Editor:** one player, contextual property tools and real timeline. Preserve caption correction, safe-margin controls, branding positions, sticker timing, audio comparison, trim and explicit save/render. Pending tools stay absent until a validated renderer supports them.
5. **Quality evaluation:** use permitted real podcast, gaming and Urdu/Hindi footage. Review hook/context/payoff, repeated ideas, clipped speech, crop loss, caption alignment, audio artifacts and export quality. Compare outputs on the same source and requested duration; scores alone cannot establish quality.
6. **Infrastructure:** preserve the present architecture for local use. For hosted processing, add durable job state, resource limits, isolated files, signed media delivery and measured throughput. A Vercel frontend alone does not replace a long-running video worker.

## Implementation routes and order

**Retain the local/open-source pipeline:** closest to the user's existing free/no-login preference. Upgrade selection, tracking, alignment and editing incrementally. The previously observed two-core CPU and lack of CUDA limit local throughput; do not promise cloud-service speed from UI changes.

**Optional provider-backed processing:** could be investigated because Kixy discloses a video-processing provider. This is a proposal, not proof that the same API/configuration reproduces Kixy's results. It would require supported API documentation, credentials, budget, upload/privacy decisions and an output benchmark. No API integration, signup or paid call was performed.

Recommended order: simplify the create screen; improve clip-specific result presentation; evaluate semantic selection on representative footage; implement measured subject tracking; improve caption timing; introduce durable hosted workers if deployment is wanted. Defer billing, email notifications, MCP and generative-video modules until the core outputs meet the user's quality target.

The useful target is the ease of its input-to-preview workflow plus independently validated editing quality. Pixel similarity or changing score formatting cannot establish processing parity.

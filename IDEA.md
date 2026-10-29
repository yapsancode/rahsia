# Rahsia: private matchmaking for startups and investors

> **Status:** idea (proposal to the team), written 2026-10-29. No code yet.
> **Event:** Hacktoberfest Hack Day Kuala Lumpur, Saturday 31 Oct 2026.
> *Rahsia* is Malay for "secret".

---

## 1. One-line pitch

Startups and investors check if they fit **before** they reveal anything, using Gemma 4 running on each person's own laptop. If there is no fit, nobody learns anything. If there is a fit, the AI drafts the introduction and saves a receipt of what was shared.

**The one sentence for judges:**
> "We turn a noisy pitch inbox into a short list of real fits, without any secret leaving the laptop."

---

## 2. The problem

### The story (from our own team)
We pitched our idea to a large company. We never knew their real agenda: did they want to invest, partner, or just hire our team as staff? And we are still not sure what happened to our idea afterwards. Many founders feel the same.

### Three pains

| # | Pain | Who feels it |
|---|---|---|
| 1 | **Hidden agenda.** Founders do not know if the other side wants to invest, partner or hire the team. | Founders |
| 2 | **Fear of sharing.** Founders hold back real details because they fear the idea will be copied. Investors also hold back their real budget and focus. So the first meeting is shallow. | Both sides |
| 3 | **Noise.** On an open (online) channel there are too many pitches. Many get postponed or skipped, even good ones. Founders also waste time on investors who never fit. | Both sides |

### Evidence we found (checked 2026-10-27)
- Southeast Asia had its **lowest number of startup deals in at least 8 years in Q1 2026** (98 equity deals). Source: DealStreetAsia.
- Venture deal value in the region fell **33.9% in 2025**. Reasons given: tighter due diligence and less cross-border investing.
- Partnerships often **stall between the first handshake and the pilot** (Start2). There is a gap between "innovation readiness" and "procurement readiness" (Bernama).

### Not yet proven (we must check)
- How many pitches an investor or accelerator really gets each month, and how many they read. **We have no number yet.** Ask 2-3 people.
- Whether anyone already sells this. We did one search only. See section 12.

---

## 3. Which hackathon problem this solves

Every team must solve one of two Startup ASEAN problems (from Cradle). We pick **Problem 1**:

> **Outcome conversion:** How can Startup ASEAN convert ecosystem connections into measurable outcomes, including investments, commercial partnerships, market expansion and cross-border POCs?

Our answer: connections fail early because nobody dares to share. Rahsia makes the first step safe and fast, so more connections reach a real conversation.

### Event facts (from the event pages)
- Date and place: Sat 31 Oct 2026, DOJO Coworking, Menara Amplewest, Jalan P. Ramlee, Kuala Lumpur.
- Sprint: **11:00 to 15:00**. Submit by **15:00**. Finalists demo for **5 minutes** each (16:00 to 17:15).
- Everyone builds with **Gemma 4 / open-weight AI**. Two categories: *Best Open-Source AI Project* and *Best Use of Gemma 4*. Judged together; **top 5 teams** win.
- Teams of 4. The page says people register alone on MLH and are **matched at random** on the day.
- Judging criteria are **not published**. We aim at: wow in 30 seconds, technical depth, working demo, numbers, memorable.

---

## 4. Who uses it, and what they enter

### Two sides
- **Side A: the seeker.** A startup or candidate team looking for money, a partner, mentorship or a place in a programme.
- **Side B: the provider.** An investor, accelerator, angel group or corporate venture team.

### What each side tells their own laptop (private)
| Field | Seeker example | Provider example |
|---|---|---|
| **Intent** | wants funding / partner / mentor | wants to invest / partner / hire team |
| **Stage** | pre-seed | pre-seed to seed |
| **Sector** | agritech | agritech, logistics |
| **Money** | asking RM 300k to 600k | cheque RM 200k to 500k |
| **Geography** | Malaysia, then Indonesia | Malaysia, Singapore |
| **Timeline** | decide within 3 months | decide within 2 months |
| **Deal-breakers** | no acqui-hire | no pre-revenue |
| **Disclosure level** | share deck only after match | share thesis only after match |

The user can type messy notes or speak. Gemma 4 turns them into the clean fields above.

---

## 5. How it works (step by step)

```
 SEEKER LAPTOP                                   PROVIDER LAPTOP
 ─────────────                                   ───────────────
 1. messy notes                                  1. messy notes
      │  Gemma 4 (local)                              │  Gemma 4 (local)
      ▼                                               ▼
 2. clean profile (JSON, checked by schema)      2. clean profile (JSON, checked by schema)
      │  turn into "buckets"                          │  turn into "buckets"
      ▼                                               ▼
 3. ────────── private match check (local link only) ──────────
      │      each side sees ONLY: match / no match      │
      ▼                                               ▼
 4a. NO MATCH → nothing else is learned. Done.
 4b. MATCH → both agree to open up → share the overlap
      │
      ▼
 5. Gemma 4 drafts: intro message, 1-page summary, slide outline
      │
      ▼
 6. Disclosure receipt: what was shared, to whom, when (signed, time-stamped)
```

### Step details
1. **Profile builder (Gemma 4, local).** Reads messy notes and returns JSON. Output is checked against a schema in code. If a check fails, repair safe things in code before retrying.
2. **Buckets.** Turn numbers and free text into fixed choices (for example money ranges, sector list). This makes private comparison possible.
3. **Private match check.** A private set intersection (PSI) over the buckets. Each side learns the size or the overlap **only if both agree**, and nothing about non-overlapping items.
   - **Warning:** simply hashing the tags is **not private** when the list of possible tags is small, because anyone can try all of them. Use a real PSI method (for example a Diffie-Hellman based one) from a maintained library.
   - **Budget:** comparing exact amounts privately is hard. For the hackathon we compare **ranges as buckets**. We say this clearly.
4. **Result.** Only "match" or "no match", plus the overlap if both sides say yes.
5. **Drafts.** Gemma 4 writes an intro message, a one-page summary and a slide outline, using only what both sides agreed to share.
6. **Receipt.** A signed, time-stamped record: which fields were shared, with which party, at what time. Saved on the user's laptop. It is **evidence, not a legal contract**.

### How the two laptops talk
Use a **local link only**: a phone hotspot with no internet, a LAN cable, or an ad-hoc network. The demo shows "internet off, local link on". (Fully Wi-Fi off would also cut the two laptops from each other.)

---

## 6. Why Gemma 4 and local (open-weight) AI

- **Secrets stay on the laptop.** A closed cloud API would see the founder's real plan and the investor's real budget. That would break the whole idea. Open weights are the reason this works.
- **It matches the event theme:** open-source and open-weight AI, local and edge AI.
- **Gemma 4 features we can use** (Google docs, checked 2026-10-27):
  - Sizes: E2B, E4B, 12B, 26B A4B, 31B. Function calling and configurable thinking modes.
  - Image and video input on all; **native audio on E2B, E4B and 12B** (a founder can speak the pitch).
  - Context: 128K for small models, 256K for medium models. 140+ languages (Malay, Mandarin, English mix).
  - Approx. memory at 4-bit: **E2B ~2.9 GB, E4B ~4.5 GB, 12B ~6.7 GB** (weights only).
- **Model choice (to test):** try E4B first (fast), then 12B if quality is not enough. Decide by a fair test, not by feeling. Run each model twice on the same inputs first, to measure how much it disagrees with itself.
- **Practical:** download the model files **before** Saturday. Venue Wi-Fi may be slow.

---

## 7. Demo plan (5 minutes)

| Time | What judges see |
|---|---|
| 0:00 | The story: "We pitched, and never knew their real agenda." One slide, one number. |
| 0:45 | Two laptops. Internet off, local link on. |
| 1:15 | Seeker types messy notes. Gemma builds the profile on screen. |
| 1:45 | Provider does the same (different laptop). |
| 2:15 | **No-match case:** both screens show "no match". A network monitor shows almost nothing was sent. |
| 3:00 | **Match case:** both agree. Overlap appears. The draft intro and slide outline appear. |
| 3:45 | Show the disclosure receipt. |
| 4:15 | Numbers slide (see section 8). |
| 4:45 | What we do next: first customer, pilot with an accelerator. |

---

## 8. What we measure (the "numbers, not promises" part)

**Rule:** write the pass rule **before** reading any result. The outside judge is an **answer key written by hand before the AI runs**.

| Measure | How | Provisional pass rule |
|---|---|---|
| **Match accuracy** | 30 fake profile pairs; we decide the right answer by hand first. Compare with an "oracle" that can see everything. | Agrees with the oracle on at least 90% of pairs |
| **Leakage** | Count the fields the other side learns when the answer is "no match". Compare with a normal online form (which shows everything). | 0 fields on no-match (the normal form: all fields) |
| **Profile quality** | 20 messy notes (English, Malay, mixed). Compare fields to the hand-written answer. | At least 85% of fields correct |
| **Invented facts** | Count facts in the draft that were not in the shared overlap. | 0 |
| **Speed** | Seconds from notes to profile, and to draft. | Under 30 seconds each on a laptop |
| **Interview proof** | Short chats with real founders/investors. | At least 3 of 5 say the pain is real |

Numbers above are targets. If we miss, we report the real number. A missed target with honest numbers is a good result.

---

## 9. Build plan

### The smallest demo for 4 hours (11:00 to 15:00)
1. Profile builder: notes in, checked JSON out.
2. Private match check on bucketed fields (one library, no custom cryptography).
3. Simple screen for two roles.
4. Draft generator using only the shared overlap.
5. Receipt file (hash + time + signature).

### Stretch (only if time)
- Voice input (Gemma native audio).
- Malay and Mandarin mixed notes.
- Network monitor panel inside the demo.
- Provider side with several startup profiles ("short list").

### Roles for 4 people
1. **Profile builder:** Gemma prompts, schema, repair, model test.
2. **Matching engine:** buckets and private match check.
3. **Screen and receipt:** two-role UI, draft view, receipt.
4. **Numbers and pitch:** answer key, leakage count, story and slides.

If the random team differs from ours, the roles still work.

---

## 10. Honest limits (say these out loud to judges)

- It **does not stop idea theft.** It lets people share less, only after both agree, and it leaves evidence.
- The hackathon privacy is **demo level**, not bank-grade. We say what it protects and what it does not.
- After a match is revealed, the other side knows what was shared. We cannot take it back.
- Budget matching uses ranges, not exact numbers.
- The receipt is evidence, not a contract. A lawyer is still needed for real disputes.
- A small local model can make mistakes reading messy notes. The person must review the profile before it is used.

### Questions judges may ask
| Question | Answer |
|---|---|
| Does it stop people stealing ideas? | No. It reduces what is shared early, and records what was shared. |
| Why not a cloud API? | Then the secret leaves the laptop. Open weights are why this works. |
| Is this just encryption? | The private check is the easy part. The hard part is turning messy human notes into clean comparable profiles reliably. We measure that. |
| Who pays? | See section 11. |
| What if only one side uses it? | Then it is a normal profile and draft tool. The privacy part needs both sides, so we start with one accelerator. |

---

## 11. After the hackathon: the startup path

*We will continue even if we lose.*

- **First customer:** one accelerator or angel group. Reason: they receive many pitches (to be confirmed) and can bring both sides. Cradle is a possible first contact.
- **Who pays:** providers (accelerators, angel networks, corporate venture teams) with a subscription per seat. Seekers use it free.
- **Cold start (the hard part):** privacy matching needs both sides. Start with one provider who invites startups. Do not wait for a public network.
- **Hard to copy:** the profile schema, match outcome data, and trust.
- **Later modules (from our earlier ideas):**
  - *Pilot Passport:* after a match, turn the meeting into a pilot plan and track conversion.
  - *Grant Autopilot:* the same private-profile idea applied to grants.

---

## 12. Open questions and to-do

- [ ] Ask the KrackedDevs organisers: can our pre-formed team stay together? Is any pre-work allowed (research and data only, or code too)?
- [ ] Interview 2-3 investors/accelerator staff: pitches per month, pitches read, what makes them skip.
- [ ] Interview 3 founders: what they hid in their last pitch and why.
- [ ] Search competitors properly (private matchmaking, pitch-screening tools, deal-room tools). **Not done yet.**
- [ ] Choose the PSI library (maintained, simple). No custom cryptography.
- [ ] Choose the model runner (for example Ollama or LM Studio) and pre-download E4B and 12B.
- [ ] Write the answer key: 30 profile pairs and 20 messy notes (English, Malay, mixed).
- [ ] Check the official MLH page again on Friday for new rules or tracks.

---

## 13. Sources

- Event site: https://hacktoberfest.krackeddevs.com
- MLH event page: https://events.mlh.com/events/14817-hacktoberfest-hack-day-kuala-lumpur
- Gemma 4 docs: https://ai.google.dev/gemma/docs/core
- DealStreetAsia, SE Asia deal review Q1 2026: https://www.dealstreetasia.com/stories/southeast-asia-deal-review-q1-2026-summary-481038
- Start2, corporate-startup partnerships: https://www.start2.group/blog/making-corporate-startup-sustainability-partnerships-work---8-insights-from-the-field-in-southeast-asia
- Bernama, innovation vs procurement readiness: https://bernama.com/lite/news.php?id=2518144
- Cradle, Startup ASEAN: https://cradle.com.my/?p=15796

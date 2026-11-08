# Cheap&Easy Growthbot — automated social posting starter

**What it does:** uses 108 pre-rendered images and 36 original, product-linked tips covering three Cheap&Easy products. When connected, one unique image post is added to each Buffer channel's queue daily (Facebook, Instagram Professional, Pinterest). Each channel stops after 36 unique posts instead of endlessly recycling content. This is a **first-phase posting engine**, not a system that autonomously creates new products or guarantees sales.

**Status on download:** PREVIEW ONLY. It will never publish until you explicitly set the GitHub repository variable `LIVE_POSTING` to `true`.

**Cost:** Buffer Free currently allows 3 accounts and 10 queued posts/account; GitHub Actions for a public repo currently has free standard-runner minutes. Terms may change. Instagram must be Professional for auto-publish. Buffer may require manual action for certain media types. Scheduled GitHub tasks may occasionally be late or missed.

## Step-by-step setup (do not publish until a preview succeeds)

1. Create a free Buffer account at https://buffer.com and connect a Cheap&Easy Facebook Page, professional Instagram account and Pinterest business account (max three free). Set **one daily posting time** for each channel in Buffer. On Instagram, put the Cheap&Easy Whop storefront link in your bio (Instagram caption links are not clickable). For Pinterest, create just one public board to start, e.g. `Cheap&Easy Digital Guides`.
2. Open **products.json** and replace each `"url": ""` with that product's real PUBLIC Whop checkout/product URL (three required). Test the URLs in a private browser. Do not put your API key in this file.
3. Create a GitHub account if needed. Extract this project ZIP locally. Install GitHub Desktop (https://desktop.github.com/), use File → Add local repository; when prompted to make it a Git repo, accept, then **Publish repository** as `cheapeasy-growthbot` with **Keep this code private unchecked**. Public status lets Buffer fetch image URLs. **Never upload API keys, private documents or customer data** to it.
4. In Buffer, go to Settings → API and create a personal API key. Keep it secret. In GitHub repo **Settings → Secrets and variables → Actions → Secrets**, create repository secret named `BUFFER_API_KEY` and paste the key. Do not share it in chat.
5. Go to GitHub repo **Actions**, choose `CheapEasy Growthbot — daily scheduled queue`, select **Run workflow**. Initially it runs in **PREVIEW ONLY** and will print planned posts without publishing. Check images in the public repo and make sure links in `products.json` are correct. If using a name other than `main` for the default branch, add an Action variable `GH_BRANCH` or rename branch to `main` (GitHub Desktop normally uses main).
6. Once preview is correct, create an **Actions → Variables** repository variable `LIVE_POSTING` with the exact value `true`. If Buffer belongs to multiple organisations, set `BUFFER_ORG_ID`. If Pinterest has multiple boards, set `PINTEREST_BOARD_ID` to the correct ID (see https://developers.buffer.com/types/PinterestPostMetadataInput.html).
7. Choose **Run workflow** manually again. It should queue one image post per connected channel. Check each Buffer queue, verify the image and captions, and verify Instagram is set to **Automatic** rather than **Notify**. When satisfied, leave it enabled: GitHub Actions runs daily at approximately 08:37 UTC, and Buffer publishes at your chosen schedule.

## Important limitations

- **No secret tokens in public GitHub code.** API key goes in Actions Secrets.
- When the queue is full, Buffer can reject the post; it will be retried next run. Errors print in Actions logs.
- GitHub's scheduled Actions may be delayed/dropped and can be disabled after 60 days without repo activity. Inspect the Actions logs periodically.
- The bot *queues only*. It doesn't generate new copy after the 36-item pool is exhausted, reply to comments, or automatically measure Whop sales. Add those later as separate, tested modules.
- Hospital content is an independent, non-NHS medical-admin organiser. Do not make patient-outcome or treatment claims.
- Products can change price; the bot deliberately doesn't advertise a price in captions, preventing price mismatch.
- Whop may report traffic and sales attribution differently from UTM tags. Test the entire checkout funnel before relying on analytics.

## Files
- `schedule_posts.py`: Buffer API scheduler (standard library only)
- `render_media.py`: regenerates graphics from reviewed tips (requires Pillow and NumPy)
- `products.json`: reviewed topic pool & product links; add all three Whop URLs
- `media/`: 108 already rendered images, hosted publicly after upload
- `covers/`: product covers for graphics
- `state/posted.json`: queue progress, committed after each successful run
- `.github/workflows/queue-posts.yml`: daily cloud scheduler

### Technical proof points
Buffer API: https://developers.buffer.com/guides/posts-and-scheduling.html
Buffer image posts: https://developers.buffer.com/examples/create-image-post.html
Pinterest board required: https://developers.buffer.com/types/PinterestPostMetadataInput.html
GitHub scheduled workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

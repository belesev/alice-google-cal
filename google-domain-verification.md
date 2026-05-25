# Google Domain Verification for OAuth Consent Screen

## 1. Add custom domain to GitHub Pages

In your repo settings → Pages → Custom domain → enter `belesev.dev`. GitHub will create a `CNAME` file. At your registrar, add DNS records:

```
Type: A
Name: @
Values: 185.199.108.153
        185.199.109.153
        185.199.110.153
        185.199.111.153
```

## 2. Verify domain ownership for Google

Go to [Google Search Console](https://search.google.com/search-console) → Add property → enter your domain → verify via DNS TXT record (your registrar's DNS panel). This satisfies "verify ownership of your homepage."

## 3. Update the OAuth consent screen

| Field | Value |
|---|---|
| Homepage URL | `https://belesev.dev` |
| Privacy policy URL | `https://belesev.dev/privacy.html` |

The `privacy.html` in this repo will be served correctly from the custom domain once GitHub Pages is configured.

## 4. Re-submit for verification.

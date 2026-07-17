// Supabase Edge Function: send-help-email
// Accepts POST { user_email, message } and forwards via Resend API.
//
// Required secrets (set via `supabase secrets set`):
//   RESEND_API_KEY  — your Resend API key
//   ADMIN_EMAIL     — the email address to deliver help requests to

const RESEND_API_URL = "https://api.resend.com/emails";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
  const ADMIN_EMAIL = Deno.env.get("ADMIN_EMAIL");

  if (!RESEND_API_KEY || !ADMIN_EMAIL) {
    console.error("[send-help-email] Missing RESEND_API_KEY or ADMIN_EMAIL secret");
    return new Response(
      JSON.stringify({ error: "Server misconfiguration: email not set up" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  let body: { user_email?: string; message?: string };
  try {
    body = await req.json();
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid JSON body" }),
      { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  const user_email = (body.user_email || "").trim();
  const message = (body.message || "").trim();

  if (!user_email || !message) {
    return new Response(
      JSON.stringify({ error: "user_email and message are required" }),
      { status: 422, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  const submittedAt = new Date().toISOString();

  const emailPayload = {
    from: "ShieldDB Help <onboarding@resend.dev>",
    to: [ADMIN_EMAIL],
    reply_to: [user_email],
    subject: "[Job Board App] New User Request / Feedback",
    text: [
      `Sender User Email: ${user_email}`,
      `Date/Time submitted: ${submittedAt}`,
      "",
      "Message/Request Content:",
      message,
    ].join("\n"),
  };

  try {
    const resendRes = await fetch(RESEND_API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(emailPayload),
    });

    if (!resendRes.ok) {
      const errText = await resendRes.text();
      console.error(`[send-help-email] Resend API error: ${resendRes.status} ${errText}`);
      return new Response(
        JSON.stringify({ error: "Failed to send email", details: errText }),
        { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const data = await resendRes.json();
    console.log(`[send-help-email] Email sent via Resend, id=${data.id}`);

    return new Response(
      JSON.stringify({ status: "sent", detail: "Your message has been sent successfully." }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error(`[send-help-email] Unexpected error: ${err}`);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

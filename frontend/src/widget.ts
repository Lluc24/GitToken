import type { GithubLogin } from "./login";
import { agentsPath, profilePath, userPath } from "./paths";

const profileRefreshMinutes = 6 * 60;
const errorRefreshMinutes = 15;

/** Post: a Scriptable (https://docs.scriptable.app) script that draws login's tokens, rarity and top agents from the /v1/users and /v1/agents routes. */
export function scriptableWidgetScript(
  origin: string,
  login: GithubLogin,
): string {
  return `/* GitToken widget for ${login}. Paste into a new Scriptable script, then add a Scriptable widget that runs it. */
const widget = new ListWidget();
widget.url = ${JSON.stringify(`${origin}${profilePath(login)}`)};
widget.backgroundColor = Color.dynamic(new Color("#ffffff"), new Color("#0b0b0f"));
const textColor = Color.dynamic(new Color("#0b0b0f"), Color.white());

function addText(text, font, opacity) {
  const line = widget.addText(text);
  line.font = font;
  line.textColor = textColor;
  line.textOpacity = opacity;
  line.minimumScaleFactor = 0.5;
  line.lineLimit = 1;
}

/* Python's round() and format() round exact halves to even; JavaScript rounds them up. */
function roundHalfEven(value) {
  const floor = Math.floor(value);
  const fraction = value - floor;
  return fraction > 0.5 || (fraction === 0.5 && floor % 2 === 1) ? floor + 1 : floor;
}

/* Matches _format_tokens in backend/src/gittoken/badge.py. */
function formatTokens(tokens) {
  for (const [threshold, suffix] of [[1e9, "B"], [1e6, "M"], [1e3, "K"]]) {
    if (tokens >= threshold) {
      const quotient = tokens / threshold;
      const isTie = Number.isInteger(quotient * 4) && !Number.isInteger(quotient * 2);
      const text = isTie ? (roundHalfEven(quotient * 10) / 10).toFixed(1) : quotient.toFixed(1);
      return text.replace(/\\.0$/, "") + suffix;
    }
  }
  return String(tokens);
}

/* Matches _rows and _MAX_ROWS in backend/src/gittoken/badge.py: tokens_by_agent comes largest first. */
function agentRows(profile, nameByAgent) {
  const row = (name, tokens) => ({
    name,
    tokens,
    percent: roundHalfEven((profile.total_tokens ? tokens / profile.total_tokens : 0) * 100),
  });
  const rows = Object.entries(profile.tokens_by_agent).map(([agent, tokens]) => row(nameByAgent[agent], tokens));
  if (rows.length > 2) {
    return [rows[0], row("Others", rows.slice(1).reduce((sum, other) => sum + other.tokens, 0))];
  }
  return rows;
}

function refreshAfterMinutes(minutes) {
  widget.refreshAfterDate = new Date(Date.now() + minutes * 60 * 1000);
}

async function loadResponse(url) {
  const request = new Request(url);
  const body = await request.load();
  return { statusCode: request.response.statusCode, body };
}

function drawProfile(user, agents) {
  if (user.statusCode === 200 && agents.statusCode === 200) {
    const profile = JSON.parse(user.body.toRawString());
    const nameByAgent = Object.fromEntries(JSON.parse(agents.body.toRawString()).map(({ agent, name }) => [agent, name]));
    addText(formatTokens(profile.total_tokens), Font.boldSystemFont(30), 1);
    addText(profile.rarity, Font.mediumSystemFont(13), 0.8);
    widget.addSpacer();
    for (const row of agentRows(profile, nameByAgent)) {
      addText(row.name + " " + formatTokens(row.tokens) + " · " + row.percent + "%", Font.systemFont(11), 0.8);
    }
    refreshAfterMinutes(${profileRefreshMinutes});
  } else {
    const statusCode = user.statusCode === 200 ? agents.statusCode : user.statusCode;
    addText(user.statusCode === 404 ? "No such GitHub user" : "Couldn't load tokens (HTTP " + statusCode + ")", Font.systemFont(12), 1);
    refreshAfterMinutes(${errorRefreshMinutes});
  }
}

function drawUnreachable() {
  addText("Couldn't reach GitToken", Font.systemFont(12), 1);
  refreshAfterMinutes(${errorRefreshMinutes});
}

/* The rejection handler covers only the requests, so a bug in drawProfile still surfaces as an error. */
await Promise.all([
  loadResponse(${JSON.stringify(`${origin}${userPath(login)}`)}),
  loadResponse(${JSON.stringify(`${origin}${agentsPath}`)}),
]).then(([user, agents]) => drawProfile(user, agents), drawUnreachable);
widget.addSpacer();
addText(${JSON.stringify(`@${login} · GitToken`)}, Font.systemFont(11), 0.6);

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentSmall();
}
Script.complete();
`;
}

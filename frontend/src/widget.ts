import palette from "../../backend/src/gittoken/templates/palette.json";
import type { GithubLogin } from "./login";
import { agentsPath, profilePath, userPath } from "./paths";

const profileRefreshMinutes = 6 * 60;
const errorRefreshMinutes = 15;
// The narrowest small widget (141pt) less its rim, card and panel padding, as stacks take sizes in points.
const barTrackWidthPoints = 96;

/** Post: a Scriptable (https://docs.scriptable.app) script that draws login's tokens, rarity and top agents from the /v1/users and /v1/agents routes. */
export function scriptableWidgetScript(
  origin: string,
  login: GithubLogin,
): string {
  return `/* GitToken widget for ${login}. Paste into a new Scriptable script, then add a Scriptable widget that runs it. */
const palette = ${JSON.stringify(palette)};
const widget = new ListWidget();
widget.url = ${JSON.stringify(`${origin}${profilePath(login)}`)};
widget.setPadding(2, 2, 2, 2);
const card = widget.addStack();
card.layoutVertically();
card.cornerRadius = 20;
card.setPadding(12, 12, 12, 12);

/* Mirrors badge.svg.jinja and card.jinja in backend/src/gittoken/templates. */
function themed(pick, alpha = 1) {
  return Color.dynamic(new Color(pick(palette.palettes.light), alpha), new Color(pick(palette.palettes.dark), alpha));
}

function mixHex(baseHex, overHex, overAlpha) {
  const channel = (hex, index) => parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16);
  return "#" + [0, 1, 2].map((index) => Math.round(channel(baseHex, index) * (1 - overAlpha) + channel(overHex, index) * overAlpha).toString(16).padStart(2, "0")).join("");
}

function gradient(colors, locations, endPoint) {
  const linearGradient = new LinearGradient();
  linearGradient.colors = colors;
  linearGradient.locations = locations;
  linearGradient.startPoint = new Point(0, 0);
  linearGradient.endPoint = endPoint;
  return linearGradient;
}

function drawCard(rimColors, tintColor) {
  widget.backgroundGradient = gradient(
    [themed((theme) => rimColors(theme)[0]), themed((theme) => mixHex(theme.background, rimColors(theme)[1], 0.5)), themed((theme) => rimColors(theme)[2])],
    [0, 0.5, 1],
    new Point(1, 1),
  );
  card.backgroundGradient = gradient(
    [themed((theme) => mixHex(theme.background, tintColor(theme), 0.22)), themed((theme) => theme.background), themed((theme) => theme.background)],
    [0, 0.7, 1],
    new Point(0, 1),
  );
}

function addLine(stack, text, font, color) {
  const line = stack.addStack();
  const lineText = line.addText(text);
  lineText.font = font;
  lineText.textColor = color;
  lineText.minimumScaleFactor = 0.5;
  lineText.lineLimit = 1;
  line.addSpacer();
  return line;
}

function addBar(stack, fillWidthPoints, barColors) {
  const track = stack.addStack();
  track.size = new Size(${barTrackWidthPoints}, 4);
  track.cornerRadius = 2;
  track.backgroundColor = themed((theme) => theme.ink, 0.1);
  /* Scriptable sizes a stack automatically when a dimension is 0. */
  if (fillWidthPoints > 0) {
    const fill = track.addStack();
    fill.size = new Size(fillWidthPoints, 4);
    fill.cornerRadius = 2;
    fill.backgroundGradient = gradient([themed((theme) => barColors(theme)[0]), themed((theme) => barColors(theme)[1])], [0, 1], new Point(1, 0));
  }
  track.addSpacer();
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

function drawNotice(message) {
  drawCard(() => palette.brand_rim_colors, (theme) => theme.background);
  addLine(card, ${JSON.stringify(login)}, Font.boldSystemFont(14), themed((theme) => theme.ink));
  card.addSpacer(4);
  addLine(card, message, Font.systemFont(11), themed((theme) => theme.ink, 0.62));
  card.addSpacer();
  refreshAfterMinutes(${errorRefreshMinutes});
}

function drawProfile(user, agents) {
  if (user.statusCode === 200 && agents.statusCode === 200) {
    const profile = JSON.parse(user.body.toRawString());
    const nameByAgent = Object.fromEntries(JSON.parse(agents.body.toRawString()).map(({ agent, name }) => [agent, name]));
    const rarityColors = (theme) => theme.rarities[profile.rarity];
    const accent = themed((theme) => rarityColors(theme)[0]);
    drawCard((theme) => rarityColors(theme).slice(1), (theme) => rarityColors(theme)[2]);
    addLine(card, profile.login, Font.boldSystemFont(14), themed((theme) => theme.ink));
    addLine(card, profile.rarity.toUpperCase(), Font.semiboldSystemFont(9), accent);
    addLine(card, formatTokens(profile.total_tokens), Font.boldSystemFont(22), accent);
    card.addSpacer();
    const rows = agentRows(profile, nameByAgent);
    if (rows.length > 0) {
      const panel = card.addStack();
      panel.layoutVertically();
      panel.spacing = 3;
      panel.cornerRadius = 10;
      panel.setPadding(6, 8, 6, 8);
      panel.backgroundColor = themed((theme) => theme.ink, 0.06);
      for (const row of rows) {
        const line = addLine(panel, row.name, Font.mediumSystemFont(10), themed((theme) => theme.ink));
        const value = line.addText(formatTokens(row.tokens) + " · " + row.percent + "%");
        value.font = Font.regularMonospacedSystemFont(9);
        value.textColor = themed((theme) => theme.ink, 0.85);
        value.minimumScaleFactor = 0.5;
        value.lineLimit = 1;
        const fillWidthPoints = profile.total_tokens ? Math.max(4, Math.round((${barTrackWidthPoints} * row.tokens) / profile.total_tokens)) : 0;
        addBar(panel, fillWidthPoints, (theme) => rarityColors(theme).slice(2));
      }
    }
    refreshAfterMinutes(${profileRefreshMinutes});
  } else {
    const statusCode = user.statusCode === 200 ? agents.statusCode : user.statusCode;
    drawNotice(user.statusCode === 404 ? "No such GitHub user" : "Couldn't load tokens (HTTP " + statusCode + ")");
  }
}

function drawUnreachable() {
  drawNotice("Couldn't reach GitToken");
}

/* The rejection handler covers only the requests, so a bug in drawProfile still surfaces as an error. */
await Promise.all([
  loadResponse(${JSON.stringify(`${origin}${userPath(login)}`)}),
  loadResponse(${JSON.stringify(`${origin}${agentsPath}`)}),
]).then(([user, agents]) => drawProfile(user, agents), drawUnreachable);

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentSmall();
}
Script.complete();
`;
}

import palette from "../../backend/src/gittoken/templates/palette.json";
import type { GithubLogin } from "./login";
import {
  activityPath,
  agentsPath,
  avatarUrl,
  profilePath,
  userPath,
} from "./paths";

export type WidgetFamily = "small" | "medium" | "large";

export type Widget = {
  readonly family: WidgetFamily;
  readonly script: (origin: string, login: GithubLogin) => string;
};

const profileRefreshMinutes = 6 * 60;
const errorRefreshMinutes = 15;
// Leaves room for the percent beside the bar in the narrowest small widget (141pt), as stacks take sizes in points.
const barTrackWidthPoints = 64;
const rimWidthPoints = 2;
const contentPaddingPoints = 12;
const panelPaddingPoints = 8;
// Room for "100%" in 9pt monospaced digits beside a bar.
const percentWidthPoints = 44;
const contentInsetPoints = 2 * (rimWidthPoints + contentPaddingPoints);
// iPhones 320pt wide give the narrowest medium widget Scriptable runs in, 292 by 141pt.
const narrowestWidgetWidthPoints = 292;
const narrowestMediumHeightPoints = 141;
// Keeps fixed-width content 2pt clear of each side, so fractional sizes never meet the padding.
const sideSlackPoints = 4;
const narrowestContentWidthPoints =
  narrowestWidgetWidthPoints - contentInsetPoints;
// A little under the narrowest medium widget's content height, so the photo never touches its padding.
const photoSizePoints = narrowestMediumHeightPoints - contentInsetPoints - 5;
const avatarSizePixels = 324;
// Apple's Human Interface Guidelines (Widgets, Specifications): the large widget's size on each iPhone screen in
// portrait, narrowest first.
const largeWidgetSizeByScreenPoints = [
  {
    screenWidthPoints: 320,
    screenHeightPoints: 568,
    widgetWidthPoints: 292,
    widgetHeightPoints: 311,
  },
  {
    screenWidthPoints: 360,
    screenHeightPoints: 780,
    widgetWidthPoints: 329,
    widgetHeightPoints: 345,
  },
  {
    screenWidthPoints: 375,
    screenHeightPoints: 667,
    widgetWidthPoints: 321,
    widgetHeightPoints: 324,
  },
  {
    screenWidthPoints: 375,
    screenHeightPoints: 812,
    widgetWidthPoints: 329,
    widgetHeightPoints: 345,
  },
  {
    screenWidthPoints: 390,
    screenHeightPoints: 844,
    widgetWidthPoints: 338,
    widgetHeightPoints: 354,
  },
  {
    screenWidthPoints: 393,
    screenHeightPoints: 852,
    widgetWidthPoints: 338,
    widgetHeightPoints: 354,
  },
  {
    screenWidthPoints: 414,
    screenHeightPoints: 736,
    widgetWidthPoints: 348,
    widgetHeightPoints: 357,
  },
  {
    screenWidthPoints: 414,
    screenHeightPoints: 896,
    widgetWidthPoints: 360,
    widgetHeightPoints: 379,
  },
  {
    screenWidthPoints: 428,
    screenHeightPoints: 926,
    widgetWidthPoints: 364,
    widgetHeightPoints: 382,
  },
  {
    screenWidthPoints: 430,
    screenHeightPoints: 932,
    widgetWidthPoints: 364,
    widgetHeightPoints: 382,
  },
] as const;
// SwiftUI keeps a flexible spacer at least the standard 8pt spacing tall.
const flexibleSpacerMinimumPoints = 8;
// Covers rounding in the text height estimate, which already rounds each line up.
const largeLayoutSlackPoints = 4;
// The largest avatar GitHub serves: 1.4x to 1.8x across the large photo, so it is the limit rather than a choice.
const largeAvatarSizePixels = 460;
const heatmapWidthPoints = narrowestContentWidthPoints - sideSlackPoints;
const heatmapGapPoints = 1;
// A month name at 8pt is about 15pt wide: three week columns at the grid's step of about 4.9pt.
const monthLabelMinWeeks = 3;

const agentPanelSource = `function themeNeutralHex(pick) {
  const hex = pick(palette.palettes.light);
  if (hex !== pick(palette.palettes.dark)) {
    throw new Error("palette.json: " + hex + " must be the same in both themes for a widget gradient");
  }
  return hex;
}

function drawTint(tintHex, topAlpha, fadeEnd) {
  content.backgroundGradient = gradient([new Color(tintHex, topAlpha), new Color(tintHex, 0), new Color(tintHex, 0)], [0, fadeEnd, 1], new Point(0, 1));
}

/* The rim ends differ by theme and no gradient can follow appearance, so both themes use the light ends. */
function rarityStyle(rarity) {
  const rarityColors = (theme) => theme.rarities[rarity];
  const [, rimStartHex, , rimEndHex] = rarityColors(palette.palettes.light);
  return {
    accent: themed((theme) => rarityColors(theme)[0]),
    tintHex: themeNeutralHex((theme) => rarityColors(theme)[2]),
    barEndColor: themed((theme) => rarityColors(theme)[3]),
    rimStartHex,
    rimEndHex,
  };
}

/* A start color fading out over a dynamic end color draws the same blend as the badge's two-stop bar gradient. */
function addBar(stack, trackWidthPoints, fillWidthPoints, startHex, endColor) {
  const track = stack.addStack();
  track.size = new Size(trackWidthPoints, 4);
  track.cornerRadius = 2;
  track.backgroundColor = themed((theme) => theme.ink, 0.1);
  /* Scriptable sizes a stack automatically when a dimension is 0. */
  if (fillWidthPoints > 0) {
    const fill = track.addStack();
    fill.size = new Size(fillWidthPoints, 4);
    fill.cornerRadius = 2;
    fill.backgroundColor = endColor;
    const fillStart = fill.addStack();
    fillStart.size = new Size(fillWidthPoints, 4);
    fillStart.backgroundGradient = gradient([new Color(startHex, 1), new Color(startHex, 0)], [0, 1], new Point(1, 0));
  }
  track.addSpacer();
}

/* Matches _rows and _MAX_ROWS in backend/src/gittoken/badge.py: tokens_by_agent comes largest first. */
function agentRows(profile, agents) {
  const nameByAgent = Object.fromEntries(agents.map(({ agent, name }) => [agent, name]));
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

const panelNameFontPoints = 10;
const panelValueFontPoints = 9;
const panelSpacingPoints = 2;
const panelVerticalPaddingPoints = 4;

function addAgentPanel(stack, rows, totalTokens, style, trackWidthPoints) {
  if (rows.length > 0) {
    const panel = stack.addStack();
    panel.layoutVertically();
    panel.spacing = panelSpacingPoints;
    panel.cornerRadius = 10;
    panel.setPadding(panelVerticalPaddingPoints, ${panelPaddingPoints}, panelVerticalPaddingPoints, ${panelPaddingPoints});
    panel.backgroundColor = themed((theme) => theme.ink, 0.06);
    const valueColor = themed((theme) => theme.ink, 0.85);
    const valueFont = Font.regularMonospacedSystemFont(panelValueFontPoints);
    for (const row of rows) {
      const nameLine = addLine(panel, row.name, Font.mediumSystemFont(panelNameFontPoints), themed((theme) => theme.ink));
      addText(nameLine, formatTokens(row.tokens), valueFont, valueColor);
      const barLine = panel.addStack();
      barLine.centerAlignContent();
      const fillWidthPoints = totalTokens ? Math.max(4, Math.round((trackWidthPoints * row.tokens) / totalTokens)) : 0;
      addBar(barLine, trackWidthPoints, fillWidthPoints, style.tintHex, style.barEndColor);
      barLine.addSpacer();
      addText(barLine, row.percent + "%", valueFont, valueColor);
    }
  }
}`;

const profileRimSource = `/* Iridescent rims are the ring of profile_card.jinja, without its spin. */
function drawProfileRim(rarity, style) {
  if (palette.iridescent_rarities.includes(rarity)) {
    const stops = palette.iridescent_rim_stops;
    widget.backgroundColor = new Color(stops[0][1]);
    rim.backgroundGradient = gradient(stops.map(([, hex]) => new Color(hex)), stops.map(([offset]) => offset), new Point(1, 1));
  } else {
    drawRim(style.rimStartHex, style.tintHex, 0.4, style.rimEndHex);
  }
}`;

const presentMethodByFamily: Record<WidgetFamily, string> = {
  small: "presentSmall",
  medium: "presentMedium",
  large: "presentLarge",
};

/** Post: a Scriptable (https://docs.scriptable.app) script that loads urls, then passes their bodies to the
 * `draw` function that drawSource defines; draw may use the core helpers below and those in helperSources. */
function widgetScript(
  badgeName: string,
  family: WidgetFamily,
  origin: string,
  login: GithubLogin,
  urls: readonly string[],
  helperSources: readonly string[],
  drawSource: string,
): string {
  return `/* GitToken ${badgeName} widget for ${login}. Paste into a new Scriptable script, then add a ${family} Scriptable widget that runs it. */
const palette = ${JSON.stringify(palette)};
const widgetFamily = ${JSON.stringify(family)};
const widget = new ListWidget();
widget.url = ${JSON.stringify(`${origin}${profilePath(login)}`)};
widget.setPadding(0, 0, 0, 0);
const rim = widget.addStack();
rim.setPadding(${rimWidthPoints}, ${rimWidthPoints}, ${rimWidthPoints}, ${rimWidthPoints});
const card = rim.addStack();
card.cornerRadius = 20;
card.backgroundColor = themed((theme) => theme.background);
const content = card.addStack();
content.layoutVertically();
content.setPadding(${contentPaddingPoints}, ${contentPaddingPoints}, ${contentPaddingPoints}, ${contentPaddingPoints});

/* Mirrors the SVG badges in backend/src/gittoken/templates. Scriptable gradients cannot follow light and dark mode,
   so each gradient is a theme-neutral overlay on a Color.dynamic base. */
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

/* The middle stop is exact per theme; the end stops fade out of it and use one color for both themes. */
function drawRim(startHex, middleHex, middleAlpha, endHex) {
  widget.backgroundColor = themed((theme) => mixHex(theme.background, middleHex, middleAlpha));
  rim.backgroundGradient = gradient(
    [new Color(startHex, 1), new Color(startHex, 0), new Color(endHex, 0), new Color(endHex, 1)],
    [0, 0.5, 0.5, 1],
    new Point(1, 1),
  );
}

function addText(stack, text, font, color) {
  const widgetText = stack.addText(text);
  widgetText.font = font;
  widgetText.textColor = color;
  widgetText.minimumScaleFactor = 0.5;
  widgetText.lineLimit = 1;
}

function addLine(stack, text, font, color) {
  const line = stack.addStack();
  line.centerAlignContent();
  addText(line, text, font, color);
  line.addSpacer();
  return line;
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

function refreshAfterMinutes(minutes) {
  widget.refreshAfterDate = new Date(Date.now() + minutes * 60 * 1000);
}

function parseJSON(body) {
  return JSON.parse(body.toRawString());
}

async function loadResponse(url) {
  const request = new Request(url);
  const body = await request.load();
  return { statusCode: request.response.statusCode, body };
}

function drawNotice(message) {
  drawRim(palette.brand_rim_colors[0], palette.brand_rim_colors[1], 0.5, palette.brand_rim_colors[2]);
  addLine(content, ${JSON.stringify(login)}, Font.boldSystemFont(14), themed((theme) => theme.ink));
  content.addSpacer(4);
  addLine(content, message, Font.systemFont(11), themed((theme) => theme.ink, 0.62));
  content.addSpacer();
  refreshAfterMinutes(${errorRefreshMinutes});
}

/* The first URL is always a route under /v1/users/{login}, so its 404 means the GitHub user does not exist. */
function drawResponses(responses) {
  const failed = responses.find((response) => response.statusCode !== 200);
  if (failed === undefined) {
    draw(...responses.map((response) => response.body));
    refreshAfterMinutes(${profileRefreshMinutes});
  } else {
    drawNotice(responses[0].statusCode === 404 ? "No such GitHub user" : "Couldn't load tokens (HTTP " + failed.statusCode + ")");
  }
}

function drawUnreachable() {
  drawNotice("Couldn't reach GitToken");
}

${helperSources.join("\n\n")}

${drawSource}

/* config.widgetFamily is undefined when the script runs in the app, which previews the intended size. A small
   widget fits any size, so only the larger layouts ask to be resized. */
if (config.runsInWidget && widgetFamily !== "small" && config.widgetFamily !== widgetFamily) {
  drawNotice("Add this as a " + widgetFamily + " widget");
} else {
  /* The rejection handler covers only the requests, so a bug in draw still surfaces as an error. */
  await Promise.all(${JSON.stringify(urls)}.map(loadResponse)).then(drawResponses, drawUnreachable);
}

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.${presentMethodByFamily[family]}();
}
Script.complete();
`;
}

/** Styled like badge.svg.jinja: tokens, rarity and top agents. */
export const cardWidget: Widget = {
  family: "small",
  script: (origin, login) =>
    widgetScript(
      "Card",
      cardWidget.family,
      origin,
      login,
      [`${origin}${userPath(login)}`, `${origin}${agentsPath}`],
      [agentPanelSource],
      `function draw(userBody, agentsBody) {
  const profile = parseJSON(userBody);
  const style = rarityStyle(profile.rarity);
  drawRim(style.rimStartHex, style.tintHex, 0.5, style.rimEndHex);
  drawTint(style.tintHex, 0.22, 0.7);
  addLine(content, profile.login, Font.boldSystemFont(14), themed((theme) => theme.ink));
  addLine(content, profile.rarity.toUpperCase(), Font.semiboldSystemFont(9), style.accent);
  addLine(content, formatTokens(profile.total_tokens), Font.boldSystemFont(22), style.accent);
  content.addSpacer();
  addAgentPanel(content, agentRows(profile, parseJSON(agentsBody)), profile.total_tokens, style, ${barTrackWidthPoints});
}`,
    ),
};

/** Styled like profile.svg.jinja: the photo on top, then tokens, rarity and top agents. */
export const profileWidget: Widget = {
  family: "large",
  script: (origin, login) =>
    widgetScript(
      "Profile",
      profileWidget.family,
      origin,
      login,
      [
        `${origin}${userPath(login)}`,
        `${origin}${agentsPath}`,
        avatarUrl(login, largeAvatarSizePixels),
      ],
      [agentPanelSource, profileRimSource],
      `const largeWidgetSizeByScreen = ${JSON.stringify(largeWidgetSizeByScreenPoints)};
const nameFontPoints = 18;
const rarityFontPoints = 9;
const totalFontPoints = 24;
const labelFontPoints = 8;
const photoGapPoints = 8;
const panelGapPoints = 6;
const labelGapPoints = 6;

/* Post: the large widget's size on this iPhone, or on the nearest smaller listed one, so the layout never outgrows
   the widget; an iPad, or a screen smaller than any listed, gets the narrowest. */
function largeWidgetSize() {
  const screen = Device.screenSize();
  const portraitWidthPoints = Math.min(screen.width, screen.height);
  const portraitHeightPoints = Math.max(screen.width, screen.height);
  const fittingSizes = Device.isPad() ? [] : largeWidgetSizeByScreen.filter((size) => size.screenWidthPoints <= portraitWidthPoints && size.screenHeightPoints <= portraitHeightPoints);
  const largest = fittingSizes.reduce((tallest, size) => (size.widgetHeightPoints > tallest.widgetHeightPoints ? size : tallest), largeWidgetSizeByScreen[0]);
  return new Size(largest.widgetWidthPoints, largest.widgetHeightPoints);
}

/* SF Pro's line height is about 1.2 times its point size. */
function textHeightPoints(fontPoints) {
  return Math.ceil(fontPoints * 1.2);
}

function agentPanelHeightPoints(rowCount) {
  return rowCount > 0 ? 2 * panelVerticalPaddingPoints + rowCount * (textHeightPoints(panelNameFontPoints) + textHeightPoints(panelValueFontPoints)) + (2 * rowCount - 1) * panelSpacingPoints : 0;
}

/* The photo takes every point the name, the agent panel and the label leave, as the tall badge's photo does. */
function draw(userBody, agentsBody, avatarBody) {
  const profile = parseJSON(userBody);
  const rows = agentRows(profile, parseJSON(agentsBody));
  const style = rarityStyle(profile.rarity);
  drawProfileRim(profile.rarity, style);
  drawTint(style.tintHex, 0.2, 0.6);
  const widgetSize = largeWidgetSize();
  const photoWidthPoints = widgetSize.width - ${contentInsetPoints} - ${sideSlackPoints};
  const nameRowHeightPoints = Math.max(textHeightPoints(nameFontPoints) + textHeightPoints(rarityFontPoints), textHeightPoints(totalFontPoints));
  const reservedHeightPoints = photoGapPoints + nameRowHeightPoints + panelGapPoints + agentPanelHeightPoints(rows.length) + ${flexibleSpacerMinimumPoints} + labelGapPoints + textHeightPoints(labelFontPoints) + ${largeLayoutSlackPoints};
  const photoRow = content.addStack();
  photoRow.addSpacer();
  const photo = photoRow.addImage(Image.fromData(avatarBody));
  photo.imageSize = new Size(photoWidthPoints, widgetSize.height - ${contentInsetPoints} - reservedHeightPoints);
  photo.applyFillingContentMode();
  photo.cornerRadius = 16;
  photo.borderWidth = 1;
  photo.borderColor = themed((theme) => theme.ink, 0.15);
  photoRow.addSpacer();
  content.addSpacer(photoGapPoints);
  const nameRow = content.addStack();
  nameRow.centerAlignContent();
  const nameColumn = nameRow.addStack();
  nameColumn.layoutVertically();
  addText(nameColumn, profile.login, Font.boldSystemFont(nameFontPoints), themed((theme) => theme.ink));
  addText(nameColumn, profile.rarity.toUpperCase(), Font.semiboldSystemFont(rarityFontPoints), style.accent);
  nameRow.addSpacer();
  addText(nameRow, formatTokens(profile.total_tokens), Font.boldSystemFont(totalFontPoints), style.accent);
  content.addSpacer(panelGapPoints);
  content.addSpacer();
  addAgentPanel(content, rows, profile.total_tokens, style, photoWidthPoints - 2 * ${panelPaddingPoints} - ${percentWidthPoints});
  content.addSpacer(labelGapPoints);
  const labelRow = content.addStack();
  labelRow.addSpacer();
  addText(labelRow, "GITTOKEN", Font.semiboldSystemFont(labelFontPoints), themed((theme) => theme.ink, 0.4));
  labelRow.addSpacer();
}`,
    ),
};

/** Styled like wide_profile.svg.jinja: the photo beside tokens, rarity and top agents. */
export const wideProfileWidget: Widget = {
  family: "medium",
  script: (origin, login) =>
    widgetScript(
      "Wide profile",
      wideProfileWidget.family,
      origin,
      login,
      [
        `${origin}${userPath(login)}`,
        `${origin}${agentsPath}`,
        avatarUrl(login, avatarSizePixels),
      ],
      [agentPanelSource, profileRimSource],
      `function draw(userBody, agentsBody, avatarBody) {
  const profile = parseJSON(userBody);
  const style = rarityStyle(profile.rarity);
  drawProfileRim(profile.rarity, style);
  drawTint(style.tintHex, 0.2, 0.6);
  const row = content.addStack();
  row.centerAlignContent();
  row.spacing = 12;
  const photo = row.addImage(Image.fromData(avatarBody));
  photo.imageSize = new Size(${photoSizePoints}, ${photoSizePoints});
  photo.applyFillingContentMode();
  photo.cornerRadius = 12;
  photo.borderWidth = 1;
  photo.borderColor = themed((theme) => theme.ink, 0.15);
  const details = row.addStack();
  details.layoutVertically();
  addLine(details, profile.login, Font.boldSystemFont(15), themed((theme) => theme.ink));
  addLine(details, profile.rarity.toUpperCase(), Font.semiboldSystemFont(9), style.accent);
  addLine(details, formatTokens(profile.total_tokens), Font.boldSystemFont(20), style.accent);
  details.addSpacer();
  addAgentPanel(details, agentRows(profile, parseJSON(agentsBody)), profile.total_tokens, style, ${barTrackWidthPoints});
}`,
    ),
};

/** Styled like heatmap.svg.jinja: a year of agent commits by day, shaded by tokens. */
export const activityWidget: Widget = {
  family: "medium",
  script: (origin, login) =>
    widgetScript(
      "Activity",
      activityWidget.family,
      origin,
      login,
      [`${origin}${activityPath(login)}`],
      [],
      `const daysPerWeek = 7;

/* The grid, and the month labels above it, span ${heatmapWidthPoints}pt whatever the number of weeks. */
function heatmapStepPoints(weeks) {
  return (${heatmapWidthPoints} + ${heatmapGapPoints}) / weeks;
}

/* Matches f"{agent_commits:,}" in render_heatmap in backend/src/gittoken/badge.py. */
function groupThousands(count) {
  return String(count).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ",");
}

/* Dynamic colors are not supported in DrawContext (https://docs.scriptable.app/color/#dynamic), so cells are drawn in
   colors that read on both themes: the dark palette's saturated levels, and for empty days a grey whose opacity puts
   it within a step of both palettes' empty cell over their backgrounds. */
const levelColors = [
  new Color("#a1a1a1", 0.13),
  ...palette.palettes.dark.heatmap_levels.slice(1).map(([hex, opacity]) => new Color(hex, Number(opacity))),
];

function cellsSize(columns, stepPoints) {
  const rows = Math.max(...columns.map((levels) => levels.length));
  return new Size(columns.length * stepPoints - ${heatmapGapPoints}, rows * stepPoints - ${heatmapGapPoints});
}

/* One image for the whole grid keeps the widget to a few dozen views; a stack per cell would be several hundred. */
function cellsImage(columns, stepPoints, size) {
  const context = new DrawContext();
  context.size = size;
  context.opaque = false;
  context.respectScreenScale = true;
  columns.forEach((levels, week) => {
    levels.forEach((level, weekday) => {
      const path = new Path();
      path.addRoundedRect(new Rect(week * stepPoints, weekday * stepPoints, stepPoints - ${heatmapGapPoints}, stepPoints - ${heatmapGapPoints}), 1, 1);
      context.addPath(path);
      context.setFillColor(levelColors[level]);
      context.fillPath();
    });
  });
  return context.getImage();
}

function addCells(stack, columns, stepPoints) {
  const size = cellsSize(columns, stepPoints);
  const image = stack.addImage(cellsImage(columns, stepPoints, size));
  image.imageSize = size;
}

/* A label too close to the grid's right edge to fit is left out, as its month has barely started. */
function addMonthLabels(stack, monthLabels, weeks, stepPoints, labelColor) {
  const labels = stack.addStack();
  if (monthLabels[0].week > 0) {
    labels.addSpacer(monthLabels[0].week * stepPoints);
  }
  monthLabels.forEach((label, index) => {
    const nextWeek = index + 1 < monthLabels.length ? monthLabels[index + 1].week : weeks;
    /* The grid's last column has no gap after it, so the last slot ends one gap earlier. */
    const slotWidthPoints = (nextWeek - label.week) * stepPoints - (nextWeek === weeks ? ${heatmapGapPoints} : 0);
    if (nextWeek - label.week >= ${monthLabelMinWeeks}) {
      const slot = labels.addStack();
      slot.size = new Size(slotWidthPoints, 10);
      addText(slot, label.name, Font.systemFont(8), labelColor);
      slot.addSpacer();
    } else {
      labels.addSpacer(slotWidthPoints);
    }
  });
}

/* Scriptable has no radial gradient, so the badge's three glows become one diagonal overlay, at half the light
   theme's peak opacity because each radial glow fades out from its center. */
function draw(activityBody) {
  const activity = parseJSON(activityBody);
  const [rimStartHex, rimMiddleHex, rimEndHex] = palette.brand_rim_colors;
  drawRim(rimStartHex, rimMiddleHex, 1, rimEndHex);
  const glowAlpha = Number(palette.palettes.light.heatmap_glow_opacity) / 2;
  content.backgroundGradient = gradient(palette.heatmap_glows.map(([, hex]) => new Color(hex, glowAlpha)), [0, 0.5, 1], new Point(1, 1));
  const labelColor = themed((theme) => theme.ink, 0.6);
  const header = content.addStack();
  header.centerAlignContent();
  addText(header, ${JSON.stringify(login)}, Font.boldSystemFont(14), themed((theme) => theme.ink));
  header.addSpacer();
  addText(header, formatTokens(activity.total_tokens), Font.boldSystemFont(20), themed((theme) => theme.rarities.epic[0]));
  addLine(content, "tokens across " + groupThousands(activity.agent_commits) + " agent commits in the last year", Font.systemFont(9), labelColor);
  content.addSpacer();
  const heatmapRow = content.addStack();
  heatmapRow.addSpacer();
  const heatmapBlock = heatmapRow.addStack();
  heatmapBlock.layoutVertically();
  heatmapBlock.spacing = 2;
  const weekColumns = Array.from({ length: Math.ceil(activity.levels.length / daysPerWeek) }, (_, week) => activity.levels.slice(week * daysPerWeek, (week + 1) * daysPerWeek));
  const stepPoints = heatmapStepPoints(weekColumns.length);
  addMonthLabels(heatmapBlock, activity.month_labels, weekColumns.length, stepPoints, labelColor);
  addCells(heatmapBlock, weekColumns, stepPoints);
  heatmapRow.addSpacer();
  content.addSpacer();
  const legend = content.addStack();
  legend.centerAlignContent();
  legend.spacing = 2;
  addText(legend, "GitToken", Font.systemFont(8), labelColor);
  legend.addSpacer();
  addText(legend, "Less", Font.systemFont(8), labelColor);
  addCells(legend, levelColors.map((_, level) => [level]), stepPoints);
  addText(legend, "More", Font.systemFont(8), labelColor);
}`,
    ),
};

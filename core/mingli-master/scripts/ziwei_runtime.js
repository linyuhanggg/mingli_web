#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

global.self = global;
const iztro = require(path.join(
  __dirname,
  "..",
  "vendor",
  "iztro-2.5.8",
  "iztro.min.js",
));

function timeIndex(hour) {
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    throw new Error("hour must be an integer from 0 through 23");
  }
  return hour === 23 ? 12 : Math.floor((hour + 1) / 2);
}

function main() {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const { year, month, day, hour, gender } = input;
  if (![year, month, day, hour].every(Number.isInteger)) {
    throw new Error("year, month, day, and hour must be integers");
  }
  if (!["男", "女"].includes(gender)) {
    throw new Error("gender must be 男 or 女");
  }
  const ziHourPolicy = input.ziHourPolicy || "midnight";
  if (!["midnight", "late-zi-next-day"].includes(ziHourPolicy)) {
    throw new Error("ziHourPolicy must be midnight or late-zi-next-day");
  }
  iztro.astro.config({
    yearDivide: "normal",
    horoscopeDivide: "normal",
    ageDivide: "normal",
    dayDivide: ziHourPolicy === "late-zi-next-day" ? "forward" : "current",
    algorithm: "default",
  });
  const birthTimeIndex = timeIndex(hour);
  const chart = iztro.astro.bySolar(
    `${year}-${month}-${day}`,
    birthTimeIndex,
    gender,
    true,
    "zh-CN",
  );
  const output = JSON.parse(JSON.stringify(chart));
  output.runtimeConvention = {
    ...iztro.astro.getConfig(),
    timeIndex: birthTimeIndex,
    fixLeap: true,
  };
  const compactHoroscope = (targetDate) => {
    const horoscope = chart.horoscope(targetDate);
    return JSON.parse(JSON.stringify({
        solarDate: horoscope.solarDate,
        lunarDate: horoscope.lunarDate,
        decadal: horoscope.decadal,
        age: horoscope.age,
        yearly: horoscope.yearly,
        monthly: horoscope.monthly,
        daily: horoscope.daily,
        hourly: horoscope.hourly,
    }));
  };
  if (Array.isArray(input.targetDates)) {
    output.requestedHoroscopes = Object.fromEntries(
      input.targetDates.map((targetDate) => [targetDate, compactHoroscope(targetDate)]),
    );
  } else if (input.targetDate) {
    output.requestedHoroscope = compactHoroscope(input.targetDate);
  }
  process.stdout.write(JSON.stringify(output));
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}

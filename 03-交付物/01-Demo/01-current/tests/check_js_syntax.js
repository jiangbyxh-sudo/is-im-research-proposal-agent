const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
new Function(src);
console.log("JS syntax OK");

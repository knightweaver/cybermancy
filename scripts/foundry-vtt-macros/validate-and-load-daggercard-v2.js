/**
 * Cybermancy — Daggercard Adversary & Environment Importer
 *
 * PURPOSE
 * -------
 * Recursively load Daggercard JSON bundles, translate each card into a
 * Foundry VTT / Daggerheart Actor, validate the translated Actor, and
 * import it either into the World or an Actor Compendium.
 *
 * Supported Daggercard categories:
 *   - adversary
 *   - environment
 *
 * Important:
 *   This macro expects Daggercard authoring JSON, NOT Foundry-export JSON.
 *
 * Artwork fields:
 *
 * Adversary:
 *   art.portrait -> Actor.img
 *   art.token    -> prototypeToken.texture.src
 *
 * Environment:
 *   art.image    -> Actor.img
 *                -> prototypeToken.texture.src
 *
 * Foundry target:
 *   Foundry VTT 13
 *   Daggerheart 1.2.x
 */

(async () => {

  /* ================================================================ */
  /* CONFIGURATION                                                    */
  /* ================================================================ */

  const CONFIG = {
    adversaryFolderRoot: "Adversaries",
    environmentFolderRoot: "Environments",

    fallbackAdversaryImg: "icons/svg/mystery-man.svg",
    fallbackEnvironmentImg: "icons/svg/hazard.svg",

    defaultAttackImg:
      "icons/skills/melee/unarmed-punch-fist-yellow-red.webp",

    defaultFeatureImg:
      "icons/svg/aura.svg",

    hostileAdversaryRing: true
  };


  /* ================================================================ */
  /* BASIC UTILITIES                                                  */
  /* ================================================================ */

  const esc = foundry.utils.escapeHTML;

  const duplicate =
    foundry.utils.deepClone ??
    foundry.utils.duplicate;

  const isObj = v =>
    v &&
    typeof v === "object" &&
    !Array.isArray(v);

  const isStr = v =>
    typeof v === "string" &&
    v.trim().length > 0;

  const isNum = v =>
    typeof v === "number" &&
    Number.isFinite(v);

  const lower = value =>
    String(value ?? "")
      .trim()
      .toLowerCase();

  const randomId = () =>
    foundry.utils.randomID();


  function normalizeHtml(value) {
    if (!isStr(value)) return "";

    const text = value.trim();

    // Already HTML.
    if (text.startsWith("<")) return text;

    // Preserve paragraph breaks.
    return text
      .split(/\n\s*\n/)
      .map(p => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`)
      .join("");
  }


  function textList(value) {
    if (Array.isArray(value)) {
      return value
        .filter(isStr)
        .join(", ");
    }

    return isStr(value)
      ? value
      : "";
  }


  function htmlList(value) {
    if (Array.isArray(value)) {
      const elements = value
        .filter(isStr)
        .map(v => `<li>${esc(v)}</li>`)
        .join("");

      return elements
        ? `<ul>${elements}</ul>`
        : "";
    }

    return normalizeHtml(value);
  }


  /* ================================================================ */
  /* DAGGERCARD NORMALIZATION                                         */
  /* ================================================================ */

  function normalizeRange(value) {

    const map = {
      melee: "melee",

      "very close": "veryClose",
      veryclose: "veryClose",

      close: "close",

      far: "far",

      "very far": "veryFar",
      veryfar: "veryFar"
    };

    return map[lower(value)] ?? "melee";
  }


  function normalizeActionType(value) {

    switch (lower(value)) {

      case "reaction":
        return "reaction";

      case "passive":
        return "passive";

      default:
        return "action";
    }
  }


  function normalizeDamageType(value) {

    const map = {
      phy: "physical",
      physical: "physical",

      mag: "magical",
      magic: "magical",
      magical: "magical"
    };

    return map[lower(value)] ?? null;
  }


  /* ================================================================ */
  /* DAMAGE PARSER                                                    */
  /* ================================================================ */

  /**
   * Examples accepted:
   *
   *   1d12+2 phy
   *   2d8 physical
   *   3d6 mag
   *   4 physical
   */
  function parseDamageFormula(input) {

    if (!isStr(input)) {
      return {
        parts: [],
        includeBase: false,
        direct: false
      };
    }

    const raw = input.trim();

    const match = raw.match(
      /^(\d+d\d+|\d+)(?:\s*([+-])\s*(\d+))?(?:\s+([A-Za-z]+))?$/i
    );

    /*
     * Unknown syntax:
     * preserve it as a Foundry custom formula rather than losing it.
     */
    if (!match) {

      return {
        parts: [
          {
            value: {
              custom: {
                enabled: true,
                formula: raw
              },

              multiplier: "flat",
              flatMultiplier: 1,
              dice: "d6",
              bonus: null
            },

            applyTo: "hitPoints",
            type: [],

            resultBased: false,

            valueAlt: {
              multiplier: "prof",
              flatMultiplier: 1,
              dice: "d6",
              bonus: null,

              custom: {
                enabled: false,
                formula: ""
              }
            },

            base: false
          }
        ],

        includeBase: false,
        direct: false
      };
    }


    const base = match[1];
    const sign = match[2];
    const bonusString = match[3];
    const damageTypeString = match[4];


    let dice = "d6";

    let bonus = null;

    let custom = {
      enabled: false,
      formula: ""
    };


    if (/^\d+d\d+$/i.test(base)) {

      /*
       * Foundry stores "d12", not "1d12".
       *
       * Multiple dice such as 2d8 cannot be represented cleanly in
       * the simple dice field, so preserve those as custom formulas.
       */

      const diceMatch = base.match(/^(\d+)d(\d+)$/i);

      const count = Number(diceMatch[1]);
      const sides = diceMatch[2];

      if (count === 1) {
        dice = `d${sides}`;
      }

      else {
        custom = {
          enabled: true,
          formula: base
        };
      }
    }

    else {
      custom = {
        enabled: true,
        formula: base
      };
    }


    if (bonusString) {

      const number = Number(bonusString);

      bonus =
        sign === "-"
          ? -number
          : number;
    }


    const damageType =
      normalizeDamageType(
        damageTypeString
      );


    return {

      parts: [
        {
          value: {
            custom,
            dice,
            bonus,
            multiplier: "flat",
            flatMultiplier: 1
          },

          applyTo: "hitPoints",

          type:
            damageType
              ? [damageType]
              : [],

          resultBased: false,

          valueAlt: {
            multiplier: "prof",
            flatMultiplier: 1,
            dice: "d6",
            bonus: null,

            custom: {
              enabled: false,
              formula: ""
            }
          },

          base: false
        }
      ],

      includeBase: false,
      direct: false
    };
  }


  /* ================================================================ */
  /* EXPERIENCE PARSER                                                */
  /* ================================================================ */

  /**
   * Example:
   *
   * "Sewer Ambush +2"
   *
   * becomes:
   *
   * {
   *   randomID: {
   *     name: "Sewer Ambush",
   *     value: 2
   *   }
   * }
   */
  function buildExperiences(entries) {

    const experiences = {};

    if (!Array.isArray(entries))
      return experiences;


    for (const entry of entries) {

      if (!isStr(entry))
        continue;


      const match =
        entry.match(
          /^(.*?)(?:\s*\+\s*(-?\d+))?$/
        );


      const name =
        match?.[1]?.trim();

      if (!name)
        continue;


      experiences[randomId()] = {

        name,

        value:
          Number(
            match?.[2] ?? 0
          )
      };
    }


    return experiences;
  }


  /* ================================================================ */
  /* ADVERSARY PRIMARY ATTACK                                         */
  /* ================================================================ */

  function buildAdversaryAttack(card) {

    const weapon =
      card?.stats?.weapon ?? {};


    return {

      name:
        isStr(weapon.name)
          ? weapon.name
          : "Attack",


      roll: {

        bonus:
          isNum(card?.stats?.attack)
            ? card.stats.attack
            : 0,

        type: "attack",

        trait: null,
        difficulty: null,

        advState: "neutral",

        diceRolling: {
          multiplier: "prof",
          flatMultiplier: 1,
          dice: "d6",
          compare: null,
          treshold: null
        },

        useDefault: false
      },


      range:
        normalizeRange(
          weapon.range
        ),


      damage:
        parseDamageFormula(
          weapon.damage
        ),


      img:
        CONFIG.defaultAttackImg,


      type: "attack",

      chatDisplay: false,

      _id: randomId(),

      systemPath: "actions",

      baseAction: false,

      description: "",

      originItem: {
        type: "itemCollection"
      },

      actionType: "action",

      cost: [],

      uses: {
        value: null,
        max: null,
        recovery: null,
        consumeOnSuccess: false
      },

      target: {
        type: "any",
        amount: null
      },

      effects: [],

      save: {
        trait: null,
        difficulty: null,
        damageMod: "none"
      }
    };
  }


  /* ================================================================ */
  /* FEATURE TRANSLATION                                              */
  /* ================================================================ */

  /**
   * Daggercard:
   *
   * {
   *   "name": "Death Roll",
   *   "action": "Action",
   *   "description": "..."
   * }
   *
   * becomes an embedded Foundry Item(type="feature").
   */
  function buildFeatureItem(feature) {

    const featureId =
      randomId();

    const actionId =
      randomId();


    const action = {

      type: "effect",

      _id: actionId,

      systemPath: "actions",

      description:
        normalizeHtml(
          feature.description
        ),

      chatDisplay: true,

      actionType:
        normalizeActionType(
          feature.action
        ),

      cost: [],

      uses: {
        value: null,
        max: "",
        recovery: null,
        consumeOnSuccess: false
      },

      effects: [],

      target: {
        type: "any",
        amount: null
      },

      name:
        feature.name ??
        "Feature",

      img:
        feature?.art?.image ??
        CONFIG.defaultFeatureImg,

      range: "",

      baseAction: false,

      originItem: {
        type: "itemCollection"
      }
    };


    return {

      name:
        feature.name ??
        "Feature",

      type: "feature",

      _id:
        featureId,

      img:
        feature?.art?.image ??
        CONFIG.defaultFeatureImg,


      system: {

        description:
          normalizeHtml(
            feature.description
          ),

        resource: null,

        actions: {
          [actionId]:
            action
        },

        originItemType: null,

        attribution: {},

        multiclassOrigin: false
      },


      effects: [],

      folder: null,

      sort: 0,

      flags: {},

      ownership: {
        default: 0
      }
    };
  }


  /* ================================================================ */
  /* PROTOTYPE TOKEN BUILDERS                                         */
  /* ================================================================ */

  function commonToken(name, image) {

    return {

      name,

      displayName: 0,

      actorLink: false,

      width: 1,
      height: 1,


      texture: {

        src: image,

        anchorX: 0.5,
        anchorY: 0.5,

        offsetX: 0,
        offsetY: 0,

        fit: "contain",

        scaleX: 1,
        scaleY: 1,

        rotation: 0,

        tint: "#ffffff",

        alphaThreshold: 0.75
      },


      lockRotation: false,

      rotation: 0,

      alpha: 1,

      disposition: -1,

      displayBars: 0,


      bar1: {
        attribute:
          "resources.hitPoints"
      },


      bar2: {
        attribute:
          "resources.stress"
      },


      light: {

        negative: false,

        priority: 0,

        alpha: 0.5,

        angle: 360,

        bright: 0,

        color: null,

        coloration: 1,

        dim: 0,

        attenuation: 0.5,

        luminosity: 0.5,

        saturation: 0,

        contrast: 0,

        shadows: 0,


        animation: {
          type: null,
          speed: 5,
          intensity: 5,
          reverse: false
        },


        darkness: {
          min: 0,
          max: 1
        }
      },


      sight: {

        enabled: false,

        range: 0,

        angle: 360,

        visionMode: "basic",

        color: null,

        attenuation: 0.1,

        brightness: 0,

        saturation: 0,

        contrast: 0
      },


      detectionModes: [],


      occludable: {
        radius: 0
      },


      turnMarker: {
        mode: 1,
        animation: null,
        src: null,
        disposition: false
      },


      movementAction: null,

      flags: {},

      randomImg: false,

      appendNumber: false,

      prependAdjective: false
    };
  }


  function buildAdversaryToken(
    card,
    portrait,
    token
  ) {

    const t =
      commonToken(
        card.name,
        token ||
        portrait ||
        CONFIG.fallbackAdversaryImg
      );


    t.ring = {

      enabled:
        CONFIG.hostileAdversaryRing,

      colors: {

        ring:
          CONFIG.hostileAdversaryRing
            ? "#8f0000"
            : null,

        background: null
      },

      effects: 1,

      subject: {
        scale: 0.8,
        texture: null
      }
    };


    return t;
  }


  function buildEnvironmentToken(
    card,
    image
  ) {

    const t =
      commonToken(
        card.name,
        image ||
        CONFIG.fallbackEnvironmentImg
      );


    t.ring = {

      enabled: false,

      colors: {
        ring: null,
        background: null
      },

      effects: 1,

      subject: {
        scale: 1,
        texture: null
      }
    };


    return t;
  }


  /* ================================================================ */
  /* DAGGERCARD VALIDATION                                            */
  /* ================================================================ */

  function validateCard(card) {

    const errors = [];
    const warnings = [];


    if (!isStr(card?.name))
      errors.push(
        `missing "name"`
      );


    if (!isStr(card?.category))
      errors.push(
        `missing "category"`
      );


    if (!isNum(card?.tier))
      warnings.push(
        `missing/invalid "tier"`
      );


    const category =
      lower(card?.category);


    /* ---------------- ADVERSARY ---------------- */

    if (category === "adversary") {

      if (!isObj(card?.stats))
        errors.push(
          `adversary missing stats`
        );


      if (!isNum(card?.stats?.difficulty))
        errors.push(
          `adversary missing stats.difficulty`
        );


      if (
        !Array.isArray(
          card?.stats?.thresholds
        ) ||
        card.stats.thresholds.length < 2
      )
        errors.push(
          `adversary missing stats.thresholds [major,severe]`
        );


      if (!isNum(card?.stats?.hitPoints))
        errors.push(
          `adversary missing stats.hitPoints`
        );


      if (!isNum(card?.stats?.stress))
        errors.push(
          `adversary missing stats.stress`
        );


      if (!isObj(card?.stats?.weapon))
        errors.push(
          `adversary missing stats.weapon`
        );


      if (!isStr(card?.stats?.weapon?.name))
        errors.push(
          `adversary missing stats.weapon.name`
        );


      if (!isStr(card?.stats?.weapon?.range))
        errors.push(
          `adversary missing stats.weapon.range`
        );


      if (!isStr(card?.stats?.weapon?.damage))
        errors.push(
          `adversary missing stats.weapon.damage`
        );


      if (!Array.isArray(card?.features))
        warnings.push(
          `adversary missing/invalid features[]`
        );


      if (!isStr(card?.art?.portrait))
        warnings.push(
          `adversary missing art.portrait`
        );


      if (!isStr(card?.art?.token))
        warnings.push(
          `adversary missing art.token`
        );
    }


    /* ---------------- ENVIRONMENT ---------------- */

    else if (
      category === "environment"
    ) {

      if (
        !isNum(card?.difficulty) &&
        !isNum(card?.stats?.difficulty)
      )
        warnings.push(
          `environment missing difficulty`
        );


      if (!Array.isArray(card?.features))
        warnings.push(
          `environment missing/invalid features[]`
        );


      if (!isStr(card?.art?.image))
        warnings.push(
          `environment missing art.image`
        );
    }


    else {

      errors.push(
        `unsupported category "${card?.category}"`
      );
    }


    return {
      errors,
      warnings
    };
  }


  /* ================================================================ */
  /* ADVERSARY TRANSFORMER                                            */
  /* ================================================================ */

  function transformAdversary(card) {

    const portrait =
      card?.art?.portrait ||
      CONFIG.fallbackAdversaryImg;


    const token =
      card?.art?.token ||
      portrait;


    return {

      name:
        card.name,

      img:
        portrait,

      type:
        "adversary",

      folder:
        null,


      system: {

        difficulty:
          card.stats.difficulty,


        damageThresholds: {

          major:
            card.stats.thresholds?.[0] ?? 0,

          severe:
            card.stats.thresholds?.[1] ?? 0
        },


        resources: {

          hitPoints: {
            value: 0,
            max:
              card.stats.hitPoints ?? 0,
            isReversed: true
          },


          stress: {
            value: 0,
            max:
              card.stats.stress ?? 0,
            isReversed: true
          }
        },


        motivesAndTactics:
          textList(
            card.motivesTactics
          ),


        resistance: {

          physical: {
            resistance: false,
            immunity: false,
            reduction: 0
          },


          magical: {
            resistance: false,
            immunity: false,
            reduction: 0
          }
        },


        type:
          card.type ??
          "standard",


        notes:
          "",


        hordeHp:
          1,


        experiences:
          buildExperiences(
            card.stats.experience
          ),


        bonuses: {

          roll: {

            attack: {
              bonus: 0,
              dice: []
            },

            action: {
              bonus: 0,
              dice: []
            },

            reaction: {
              bonus: 0,
              dice: []
            }
          },


          damage: {

            physical: {
              bonus: 0,
              dice: []
            },

            magical: {
              bonus: 0,
              dice: []
            }
          }
        },


        tier:
          card.tier ?? 1,


        description:
          normalizeHtml(
            card.description
          ),


        attack:
          buildAdversaryAttack(
            card
          ),


        attribution: {

          source:
            "Cybermancy Daggercard",

          page:
            null,

          artist:
            ""
        },


        criticalThreshold:
          20,


        rules: {

          conditionImmunities: {

            hidden:
              false,

            restrained:
              false,

            vulnerable:
              false
          }
        }
      },


      prototypeToken:
        buildAdversaryToken(
          card,
          portrait,
          token
        ),


      /*
       * ADVERSARY FEATURES
       */
      items:
        Array.isArray(card.features)
          ? card.features.map(
              buildFeatureItem
            )
          : [],


      effects:
        [],


      flags:
        {},


      ownership: {
        default: 0
      }
    };
  }


  /* ================================================================ */
  /* ENVIRONMENT TRANSFORMER                                          */
  /* ================================================================ */

  function transformEnvironment(card) {

    const image =
      card?.art?.image ||
      CONFIG.fallbackEnvironmentImg;


    return {

      name:
        card.name,

      type:
        "environment",

      img:
        image,

      folder:
        null,


      system: {

        attribution:
          {},


        description:
          normalizeHtml(
            card.description
          ),


        tier:
          card.tier ?? 1,


        difficulty:
          card.difficulty ??
          card?.stats?.difficulty ??
          0,


        potentialAdversaries:
          {},


        notes:
          Array.isArray(card.notes)
            ? htmlList(card.notes)
            : normalizeHtml(card.notes),


        impulses:
          Array.isArray(card.impulses)
            ? card.impulses.join(", ")
            : (card.impulses ?? ""),


        type:
          card.type ??
          "general"
      },


      prototypeToken:
        buildEnvironmentToken(
          card,
          image
        ),


      /*
       * IMPORTANT:
       *
       * Environment features must ALSO be embedded Feature Items.
       *
       * The first version of this macro accidentally used:
       *
       *     items: []
       *
       * which silently discarded environment features.
       */
      items:
        Array.isArray(card.features)
          ? card.features.map(
              buildFeatureItem
            )
          : [],


      effects:
        [],


      flags:
        {},


      ownership: {
        default: 0
      }
    };
  }


  /* ================================================================ */
  /* CARD DISPATCH                                                    */
  /* ================================================================ */

  function transformCard(card) {

    switch (
      lower(card?.category)
    ) {

      case "adversary":
        return transformAdversary(card);

      case "environment":
        return transformEnvironment(card);

      default:
        throw new Error(
          `Unsupported Daggercard category: ${card?.category}`
        );
    }
  }


  /* ================================================================ */
  /* TRANSLATED FOUNDRY VALIDATION                                    */
  /* ================================================================ */

  function validateActor(doc) {

    const errors = [];
    const warnings = [];


    if (!isStr(doc?.name))
      errors.push(
        "Actor missing name"
      );


    if (!isStr(doc?.type))
      errors.push(
        "Actor missing type"
      );


    if (!isObj(doc?.system))
      errors.push(
        "Actor missing system"
      );


    if (
      doc?.type === "adversary"
    ) {

      if (!isNum(doc?.system?.difficulty))
        errors.push(
          "Adversary missing system.difficulty"
        );


      if (
        !isObj(
          doc?.system?.damageThresholds
        )
      )
        errors.push(
          "Adversary missing system.damageThresholds"
        );


      if (
        !isObj(
          doc?.system?.resources?.hitPoints
        )
      )
        errors.push(
          "Adversary missing resources.hitPoints"
        );


      if (
        !isObj(
          doc?.system?.resources?.stress
        )
      )
        errors.push(
          "Adversary missing resources.stress"
        );


      if (
        !isObj(
          doc?.system?.attack
        )
      )
        errors.push(
          "Adversary missing system.attack"
        );
    }


    if (
      doc?.type === "environment"
    ) {

      if (
        !isNum(
          doc?.system?.difficulty
        )
      )
        warnings.push(
          "Environment missing system.difficulty"
        );


      if (
        !isNum(
          doc?.system?.tier
        )
      )
        warnings.push(
          "Environment missing system.tier"
        );
    }


    if (!Array.isArray(doc?.items))
      errors.push(
        "Actor items must be an array"
      );


    if (!isStr(doc?.img))
      warnings.push(
        "Actor missing image"
      );


    if (
      !isStr(
        doc?.prototypeToken
          ?.texture?.src
      )
    )
      warnings.push(
        "Actor missing token image"
      );


    return {
      errors,
      warnings
    };
  }


  /* ================================================================ */
  /* FILE ACCESS                                                      */
  /* ================================================================ */

  async function fetchJson(
    path
  ) {

    const assets =
      foundry.utils
        ?.getRoute
        ?.("assets");


    if (assets) {

      const url =
        `${assets}?path=${encodeURIComponent(path)}`;


      const response =
        await fetch(
          url,
          {
            cache: "no-store"
          }
        );


      if (response.ok)
        return await response.json();
    }


    const response =
      await fetch(
        path,
        {
          cache: "no-store"
        }
      );


    if (!response.ok)
      throw new Error(
        `HTTP ${response.status} for ${path}`
      );


    return await response.json();
  }


  async function* walkFolder(
    dir
  ) {

    const browse =
      await FilePicker.browse(
        "data",
        dir
      );


    for (const subdir of browse.dirs)
      yield* walkFolder(subdir);


    for (const file of browse.files) {

      if (
        file
          .toLowerCase()
          .endsWith(".json")
      )
        yield file;
    }
  }


  function isDaggercardBundle(
    json
  ) {

    return (
      isObj(json) &&
      Array.isArray(json.cards)
    );
  }


  /* ================================================================ */
  /* WORLD FOLDER SUPPORT                                             */
  /* ================================================================ */

  const worldFolderCache =
    new Map();


  async function ensureWorldFolderPath(
    names
  ) {

    let parentId =
      null;

    let folder =
      null;


    for (const name of names) {

      const key =
        `${parentId ?? "ROOT"}::${name}`;


      folder =
        worldFolderCache.get(
          key
        );


      if (!folder) {

        folder =
          game.folders.find(
            f =>
              f.type === "Actor" &&
              f.name === name &&
              (
                f.parent?.id ??
                null
              ) === parentId
          ) ??
          null;


        if (!folder) {

          folder =
            await Folder.create({
              name,
              type: "Actor",
              parent: parentId
            });
        }


        worldFolderCache.set(
          key,
          folder
        );
      }


      parentId =
        folder.id;
    }


    return folder;
  }


  /* ================================================================ */
  /* COMPENDIUM FOLDER SUPPORT                                        */
  /* ================================================================ */

  const packFolderCache =
    new Map();


  async function refreshPack(
    pack
  ) {

    try {

      await pack.getIndex?.({
        fields: ["folder"]
      });

    } catch (_error) {
      // Non-fatal.
    }
  }


  async function ensurePackFolderPath(
    pack,
    names
  ) {

    let parentId =
      null;

    let folder =
      null;


    for (const name of names) {

      const key =
        `${pack.collection}::${parentId ?? "ROOT"}::${name}`;


      folder =
        packFolderCache.get(
          key
        );


      if (!folder) {

        const folders =
          pack.folders
            ? Array.from(pack.folders)
            : [];


        folder =
          folders.find(
            f =>
              f.name === name &&
              (
                f.parent?.id ??
                null
              ) === parentId
          ) ??
          null;


        if (!folder) {

          if (
            typeof pack.createFolder ===
            "function"
          ) {

            folder =
              await pack.createFolder({
                name,
                parent: parentId
              });

          } else {

            folder =
              await Folder.create({

                name,

                type:
                  "Compendium",

                parent:
                  parentId,

                pack:
                  pack.collection
              });
          }


          await refreshPack(
            pack
          );
        }


        packFolderCache.set(
          key,
          folder
        );
      }


      parentId =
        folder.id;
    }


    return folder;
  }


  /* ================================================================ */
  /* IMPORT                                                           */
  /* ================================================================ */

  async function importActor(
    actorData,
    pack
  ) {

    const root =
      actorData.type ===
      "environment"

        ? CONFIG.environmentFolderRoot

        : CONFIG.adversaryFolderRoot;


    const subtype =
      actorData?.system?.type ??
      "Other";


    const hierarchy = [
      root,
      String(subtype)
    ];


    /* ---------------- WORLD ---------------- */

    if (!pack) {

      const folder =
        await ensureWorldFolderPath(
          hierarchy
        );


      actorData.folder =
        folder?.id ??
        null;


      return await Actor.create(
        actorData,
        {
          renderSheet: false
        }
      );
    }


    /* ---------------- COMPENDIUM ---------------- */

    const folder =
      await ensurePackFolderPath(
        pack,
        hierarchy
      );


    actorData.folder =
      folder?.id ??
      null;


    const DocClass =
      pack.documentClass ??
      game.actors.documentClass;


    const document =
      new DocClass(
        actorData
      );


    return await pack.importDocument(
      document
    );
  }


  /* ================================================================ */
  /* VALIDATION REPORT UI                                             */
  /* ================================================================ */

  function buildReport(
    results
  ) {

    const rows =
      results
        .map(
          (result, index) => {

            const messages =
              [];


            for (
              const error
              of result.errors
            )
              messages.push(
                `❌ ${error}`
              );


            for (
              const warning
              of result.warnings
            )
              messages.push(
                `⚠️ ${warning}`
              );


            const status =
              result.errors.length
                ? "ERR"
                : result.warnings.length
                  ? "WARN"
                  : "OK";


            const color =
              status === "OK"
                ? "#3bb273"
                : status === "WARN"
                  ? "#f0ad4e"
                  : "#d9534f";


            return `
              <tr>

                <td>
                  <input
                    type="checkbox"
                    name="sel"
                    value="${index}"
                    ${status !== "ERR" ? "checked" : "disabled"}
                  />
                </td>

                <td>
                  <code>${esc(result.file)}</code>
                </td>

                <td>
                  ${esc(result.cardName)}
                </td>

                <td style="
                    color:${color};
                    font-weight:600;
                ">
                  ${status}
                </td>

                <td>
                  ${
                    messages.length
                      ? messages
                          .map(
                            m =>
                              `<div>${esc(m)}</div>`
                          )
                          .join("")
                      : "(none)"
                  }
                </td>

              </tr>
            `;
          }
        )
        .join("");


    return `
      <form class="daggercard-report">

        <div
          style="
            display:flex;
            gap:.5rem;
            margin-bottom:.5rem;
          "
        >

          <button
            type="button"
            data-action="all"
          >
            Select All Valid
          </button>

          <button
            type="button"
            data-action="none"
          >
            Select None
          </button>

        </div>


        <div
          style="
            max-height:450px;
            overflow:auto;
          "
        >

          <table
            style="
              width:100%;
              border-collapse:collapse;
            "
          >

            <thead>

              <tr>

                <th></th>

                <th>
                  File
                </th>

                <th>
                  Card
                </th>

                <th>
                  Status
                </th>

                <th>
                  Messages
                </th>

              </tr>

            </thead>


            <tbody>

              ${rows}

            </tbody>

          </table>

        </div>

      </form>
    `;
  }


  /* ================================================================ */
  /* INITIAL OPTIONS DIALOG                                           */
  /* ================================================================ */

  async function getOptions() {

    const actorPacks =
      Array.from(game.packs)
        .filter(
          p =>
            p.documentName ===
            "Actor"
        );


    const packOptions = [

      `<option value="">
        Import to World
      </option>`,

      ...actorPacks.map(
        p =>
          `<option value="${p.collection}">
             ${esc(p.title)}
             —
             ${esc(p.collection)}
           </option>`
      )
    ].join("");


    const content = `

      <form>

        <div class="form-group">

          <label>
            Daggercard Folder
          </label>

          <div class="flexrow">

            <input
              type="text"
              name="folder"
            />

            <button
              type="button"
              class="filepicker"
            >
              <i class="fas fa-folder-open"></i>
            </button>

          </div>

        </div>


        <div class="form-group">

          <label>
            Target Actor Compendium
          </label>

          <select name="pack">

            ${packOptions}

          </select>

        </div>


        <div class="form-group">

          <label class="checkbox">

            <input
              type="checkbox"
              name="dryRun"
              checked
            />

            Dry Run
          </label>

        </div>

      </form>
    `;


    return await new Promise(
      resolve => {

        const dialog =
          new Dialog({

            title:
              "Cybermancy Daggercard Import",


            content,


            buttons: {

              run: {

                label:
                  "Run",

                callback:
                  html => {

                    const folder =
                      html
                        .find(
                          '[name="folder"]'
                        )
                        .val()
                        ?.trim();


                    if (!folder) {

                      ui.notifications.error(
                        "Select a folder."
                      );

                      return;
                    }


                    resolve({

                      folder,

                      pack:
                        html
                          .find(
                            '[name="pack"]'
                          )
                          .val()
                          ?.trim(),

                      dryRun:
                        html
                          .find(
                            '[name="dryRun"]'
                          )[0]
                          .checked
                    });
                  }
              },


              cancel: {

                label:
                  "Cancel",

                callback:
                  () =>
                    resolve(null)
              }
            },


            default:
              "run",


            render:
              html => {

                html
                  .find(
                    ".filepicker"
                  )
                  .on(
                    "click",
                    () => {

                      const picker =
                        new FilePicker({

                          type:
                            "folder",

                          current:
                            "data",

                          callback:
                            path => {

                              html
                                .find(
                                  '[name="folder"]'
                                )
                                .val(path);
                            }
                        });


                      picker.browse(
                        "data"
                      );
                    }
                  );
              }
          });


        dialog.render(true);
      }
    );
  }


  /* ================================================================ */
  /* MAIN RUN                                                         */
  /* ================================================================ */

  async function run(
    {
      folder,
      pack,
      dryRun
    }
  ) {

    const results =
      [];


    /* ---------------- READ ---------------- */

    for await (
      const file
      of walkFolder(folder)
    ) {

      try {

        const json =
          await fetchJson(file);


        /*
         * Ignore unrelated JSON files.
         */
        if (
          !isDaggercardBundle(json)
        )
          continue;


        for (
          const card
          of json.cards
        ) {

          const sourceValidation =
            validateCard(card);


          let errors =
            [...sourceValidation.errors];


          let warnings =
            [...sourceValidation.warnings];


          let actorData =
            null;


          if (!errors.length) {

            try {

              actorData =
                transformCard(card);


              const actorValidation =
                validateActor(actorData);


              errors.push(
                ...actorValidation.errors
              );


              warnings.push(
                ...actorValidation.warnings
              );

            }

            catch (error) {

              errors.push(
                error.message ??
                String(error)
              );
            }
          }


          results.push({

            file,

            cardName:
              card?.name ??
              "(Unnamed)",

            card,

            actorData,

            errors,

            warnings
          });
        }

      }

      catch (error) {

        results.push({

          file,

          cardName:
            "(File Error)",

          actorData:
            null,

          errors: [
            error.message ??
            String(error)
          ],

          warnings: []
        });
      }
    }


    if (!results.length) {

      ui.notifications.warn(
        "No Daggercard JSON cards found."
      );

      return;
    }


    /* ---------------- REPORT ---------------- */

    const report =
      buildReport(results);


    let selected =
      null;


    await new Promise(
      resolve => {

        /*
         * IMPORTANT:
         *
         * Build buttons dynamically.
         *
         * Do NOT put an undefined button entry into a Foundry Dialog.
         * Foundry 13 attempts to mutate every button definition and
         * throws:
         *
         * Cannot set properties of undefined (setting 'cssClass')
         */

        const buttons = {};


        if (dryRun) {

          buttons.close = {

            label:
              "Close",

            callback:
              () =>
                resolve()
          };

        } else {

          buttons.importSelected = {

            label:
              "Import Selected",

            callback:
              html => {

                selected =
                  Array.from(
                    html[0]
                      .querySelectorAll(
                        'input[name="sel"]:checked'
                      )
                  )
                  .map(
                    checkbox =>
                      Number(
                        checkbox.value
                      )
                  );


                resolve();
              }
          };


          buttons.importAll = {

            label:
              "Import All Valid",

            callback:
              () => {

                selected =
                  results
                    .map(
                      (result, index) =>
                        ({
                          result,
                          index
                        })
                    )
                    .filter(
                      x =>
                        !x.result.errors.length
                    )
                    .map(
                      x =>
                        x.index
                    );


                resolve();
              }
          };
        }


        buttons.cancel = {

          label:
            "Cancel",

          callback:
            () =>
              resolve()
        };


        const dialog =
          new Dialog({

            title:
              `Daggercard Validation (${results.length} cards)`,


            content:
              report,


            buttons,


            render:
              html => {

                const form =
                  html.find(
                    ".daggercard-report"
                  );


                form.on(
                  "click",
                  '[data-action="all"]',
                  event => {

                    event.preventDefault();


                    form
                      .find(
                        'input[name="sel"]:not(:disabled)'
                      )
                      .prop(
                        "checked",
                        true
                      );
                  }
                );


                form.on(
                  "click",
                  '[data-action="none"]',
                  event => {

                    event.preventDefault();


                    form
                      .find(
                        'input[name="sel"]'
                      )
                      .prop(
                        "checked",
                        false
                      );
                  }
                );
              }
          });


        dialog.render(true);
      }
    );


    if (
      dryRun ||
      !Array.isArray(selected)
    )
      return;


    /* ---------------- TARGET PACK ---------------- */

    const targetPack =
      pack
        ? game.packs.get(pack)
        : null;


    if (
      pack &&
      !targetPack
    )
      throw new Error(
        `Compendium not found: ${pack}`
      );


    if (
      targetPack &&
      targetPack.documentName !==
      "Actor"
    )
      throw new Error(
        "Target pack is not an Actor compendium."
      );


    if (
      targetPack?.locked
    )
      throw new Error(
        `Compendium is locked: ${targetPack.title}`
      );


    /* ---------------- IMPORT ---------------- */

    let imported =
      0;


    for (
      const index
      of selected
    ) {

      const result =
        results[index];


      if (
        !result?.actorData ||
        result.errors.length
      )
        continue;


      try {

        const created =
          await importActor(

            duplicate(
              result.actorData
            ),

            targetPack
          );


        console.log(
          `[Daggercard Imported]`,
          created?.uuid ??
          created?.id,
          result.cardName
        );


        imported++;

      }

      catch (error) {

        console.error(
          `Failed to import ${result.cardName}`,
          error
        );


        ui.notifications.error(
          `Failed: ${result.cardName}`
        );
      }
    }


    if (targetPack)
      await targetPack
        .getIndex?.({
          reload: true
        });


    ui.notifications.info(
      `Imported ${imported} Daggercard Actor${imported === 1 ? "" : "s"}.`
    );
  }


  /* ================================================================ */
  /* PUBLIC API + EXECUTION                                            */
  /* ================================================================ */

  window.CybermancyDaggercardImport = {
    run,
    transformCard,
    transformAdversary,
    transformEnvironment,
    validateCard,
    validateActor
  };


  try {

    const options =
      await getOptions();


    if (options)
      await run(options);

  }

  catch (error) {

    console.error(
      "Cybermancy Daggercard Import failed:",
      error
    );


    ui.notifications.error(
      `Daggercard import failed: ${
        error.message ??
        error
      }`
    );
  }

})();
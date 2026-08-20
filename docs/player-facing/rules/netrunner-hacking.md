# Netrunning and Device Intrusion

---

> **Playtest Rule:** Cybermancy uses more than one resolution scale for hacking. Use **Network Actions** for open-ended, remote, or operational objectives; use the existing **Device Intrusion** rules when manipulating a specific device or when the intrusion itself is an important encounter.

---

Cybermancy's hacking rules allow a Netrunner to affect the connected world without turning every digital action into a separate minigame. A Netrunner might remotely alter traffic controls, search municipal records, manipulate public information systems, or compromise a corporate network just as readily as they might take control of a nearby camera or drone.

The key question is not *how far away is the target?* It is:

> **Is there a plausible digital path to the system, and what is the Netrunner trying to make it do?**

## Which Hacking Rules Apply?

Use the fastest resolution method appropriate to the importance of the intrusion.

| Situation | Use | Typical Examples |
|---|---|---|
| Simple manipulation of an unhardened device | **Quick Device Access** | Open a door, redirect a civilian drone, access an unsecured terminal |
| Open-ended remote or operational hacking | **Network Actions** | Manipulate traffic, search records, suppress surveillance, generate a flash mob |
| The intrusion itself is an important encounter | **Detailed Device Intrusion** | Break into a protected server, defeat ICE, compromise a secured drone or turret |
| Large or persistent digital operation | **Network Actions over Extended or Strategic time** | Establish persistent corporate access, undermine city infrastructure, conduct a sustained influence campaign |

A scene can move between these scales. A Network Action that activates dangerous ICE, for example, may become a Detailed Device Intrusion.

> **Hardened Security vs. Hardened Devices:** **S3 Hardened** is a Security rating used for Network Actions. A **Hardened Device** is a classification used by the Detailed Device Intrusion rules. The concepts are related, but they are not mechanically identical.

# Network Actions

A **Network Action** is an attempt to use connected technology, information systems, communications, automation, or digital services to produce a specific outcome.

When attempting a Network Action:

1. **Declare the outcome.** State what you want to happen.
2. **Describe the digital approach.** Explain a plausible way to produce that outcome.
3. **Rate the action.** The GM determines **Access, Security, Scope, and Time**.
4. **Roll Hacking.** Roll against the Network Action Difficulty.
5. **Build Progress.** Each successful Network Action normally earns **1 Progress**.
6. **Resolve consequences.** Fear or failure may change the situation even when the objective advances.

The size of the network does not determine Scope. The **effect requested** does.

> "Hack the city's traffic network" is not a complete objective.  
> "Turn the next signal red" is **Discrete**.  
> "Gridlock downtown" is **Broad**.  
> "Take persistent control of citywide traffic" is **Systemic**.

## Access

Access measures how difficult it is to establish a usable connection to the target through the Netrunner's current route.

| Level | State | Modifier | Typical Meaning |
|---|---|---:|---|
| **A1** | **Open** | -2 | Publicly exposed, broadly accessible, or protected by weak/default credentials |
| **A2** | **Reachable** | +0 | Connected, but requires a normal entry point or authentication bypass |
| **A3** | **Restricted** | +2 | Internal, segmented, VPN-gated, privileged, or dependent on trusted systems |
| **A4** | **Heavily Restricted** | +4 | Multiple trust layers, controlled gateways, specialized credentials, or trusted hardware |

### Isolated Systems

**Isolated** is a separate state, not an Access level.

An air-gapped, local-only, or otherwise disconnected system cannot be hacked remotely until a usable foothold is created. A character might:

- plug a network spike into a terminal;
- plant a wireless bridge;
- compromise a trusted local device;
- open a maintenance port;
- physically connect equipment to an internal network.

Once a foothold exists, assign the resulting route an Access level from **A1-A4** based on its quality.

This makes physical infiltration valuable without requiring the Netrunner to be physically present. The field team can create the route; the Netrunner can operate through it remotely.

## Security

Security measures how capable the target's defenses are once the Netrunner can reach it.

| Level | State | Base Difficulty | Typical Systems |
|---|---|---:|---|
| **S1** | **Soft** | 10 | Consumer, neglected, obsolete, or poorly administered systems |
| **S2** | **Managed** | 13 | Normal corporate, municipal, or professional systems |
| **S3** | **Hardened** | 16 | Sensitive corporate, law-enforcement, or major infrastructure systems |
| **S4** | **Fortified** | 19 | Megacorp core, intelligence, black-site, or military command systems |

## Network Action Difficulty

> **Difficulty = Security Base + Access Modifier**

| Access | S1 Soft | S2 Managed | S3 Hardened | S4 Fortified |
|---|---:|---:|---:|---:|
| **A1 Open** | 8 | 11 | 14 | 17 |
| **A2 Reachable** | 10 | 13 | 16 | 19 |
| **A3 Restricted** | 12 | 15 | 18 | 21 |
| **A4 Heavily Restricted** | 14 | 17 | 20 | 23 |

**Scope does not modify the Difficulty of individual rolls.** Larger objectives are harder because they require more Progress and therefore expose the Netrunner to more rolls, more Fear, and more opportunities for defenders to respond.

## Scope and Progress

Scope measures how much effect the Netrunner is attempting to create.

| Level | Scope | Progress Required | Typical Effect |
|---|---|---:|---|
| **P1** | **Discrete** | 1 | One door, file, account, signal, device, or bounded effect |
| **P2** | **Limited** | 2 | One facility, contained subsystem, or coordinated set of targets |
| **P3** | **Broad** | 3 | A district, organization, major network, or large population |
| **P4** | **Systemic** | 5 | Citywide, corp-wide, regional, or infrastructure-scale effects |

Each successful Network Action normally earns **1 Progress**.

For multi-Progress objectives, each success represents a meaningful new stage of the operation rather than repeating the same command. A Systemic takeover of city traffic might progress through privileged access, control nodes, monitoring systems, failovers, and finally persistent authority.

### Example: Traffic Control

Creating a green-light corridor might be:

**A2 Reachable / S2 Managed / P2 Limited**

The Difficulty is **13**, and the Netrunner must earn **2 Progress**.

## Time Scale

Scope describes **how much must be accomplished**. Time describes **how quickly that work can reasonably happen**.

| Scale | Typical Duration | Examples |
|---|---|---|
| **Immediate** | Seconds | Open a door, interrupt a channel, alter one signal, hijack a device |
| **Short** | Minutes | Search a facility network, trace a user, fabricate credentials, alter related records |
| **Extended** | Hours to days | Compromise an administrative network, build an exploit, establish persistent access |
| **Strategic** | Days to weeks or longer | Undermine a major organization, control city infrastructure, sustain a large influence campaign |

An **Immediate** Network Action can normally be attempted during combat. **Short** work usually plays out across a scene. **Extended** and **Strategic** work normally occurs during investigation, travel, downtime, or as an operation of its own.

Scope and Time are independent. A Broad command may be Immediate if access already exists; a Discrete objective may take hours if the necessary information is difficult to uncover.

## Plausible Effects

Netrunning can only produce effects that the compromised technology, information, communications, or automation could plausibly cause.

- **Information:** Find, suppress, alter, correlate, fabricate, or redirect data where a plausible source exists.
- **Infrastructure:** Command connected systems only within their actual physical and software capabilities.
- **Social Systems:** Manipulate information environments, attention, and incentives; Netrunning does not directly control people's choices.
- **Money and Identity:** Records can be changed or funds moved, but audits, ledgers, identity checks, and retaliation remain real.

Remote operation is fully viable whenever a plausible route exists. Physical presence matters because it can provide better Access or create routes into systems that would otherwise be Restricted, Heavily Restricted, or Isolated.

# Consequences

Netrunning creates risk even when the Netrunner is physically far from the target.

Daggerheart consequences can arise because the roll **fails** or because it **succeeds with Fear**.

| Roll Result | Progress | Hacking Consequence |
|---|---:|---|
| **Success with Hope** | +1 | Clean success; no automatic hacking consequence |
| **Success with Fear** | +1 | GM offers two appropriate consequence vectors; the Netrunner chooses which worsens |
| **Failure with Hope** | 0 | GM offers two appropriate setbacks; the Netrunner chooses which occurs |
| **Failure with Fear** | 0 | GM imposes a serious consequence appropriate to the target and circumstances |

A Success with Fear still earns Progress. Fear complicates the success; it does not erase it.

A failed Network Action should normally change the situation rather than invite an identical reroll under identical conditions.

## Consequence Vectors

Most hacking consequences worsen one of four state tracks.

### Exposure

**Hidden → Detected → Traced → Burned**

Exposure measures how much defenders know about the intrusion and its source.

A remote Netrunner may be physically safe while still exposing identities, credentials, relays, associates, network infrastructure, or a physical connection point.

### Access

**Open → Reachable → Restricted → Heavily Restricted → Closed**

Access consequences degrade the current route.

A **Closed** route can no longer be used. Continuing the intrusion requires a new credential, pivot, exploit, or foothold.

### Security

**Soft → Managed → Hardened → Fortified**

Security consequences represent defenders actively hardening the target. Because Security sets the Base Difficulty, later Network Actions may become more difficult.

### Time

**Immediate → Short → Extended → Strategic**

Time consequences make the remaining work take longer.

Sometimes the most important consequence is not detection or damage, but that the objective can no longer be completed before events overtake it.

## Choosing Consequences

On a **Success with Fear** or **Failure with Hope**, the GM offers two consequences that are both meaningful. The Netrunner chooses which risk to absorb.

For example:

> You gain the second Progress on the traffic system. Choose: **Exposure rises from Hidden to Detected**, or **Access worsens from Reachable to Restricted**.

As a track worsens, choosing it again becomes more dangerous.

Not every consequence must advance a track. The GM may instead use a specific fictional consequence connected to the intrusion, such as:

- burning a credential, exploit, backdoor, or spoofed identity;
- activating tracing, a honeypot, malware, a security operator, or ICE;
- alerting guards, police, drones, administrators, or the owner of a compromised account;
- causing collateral effects in the physical or social world.

> **Consequences should change the situation, not simply punish the roll.**

Unless a rule specifically says otherwise, **earned Progress is permanent**.

# Spending Fear in the Network

The GM can spend Fear to exploit vulnerabilities, activate defenses, or make the intrusion matter in the physical world.

## Spend 1 Fear

| Effect | Result |
|---|---|
| **Escalate** | Advance one relevant consequence vector by one step: Exposure, Access, Security, or Time |
| **Activate Countermeasures** | Bring online tracing, a honeypot, a security operator, malicious response code, or appropriate ICE |
| **Burn an Asset** | Compromise a credential, exploit, backdoor, spoofed identity, planted device, or other asset directly involved in the intrusion |
| **Trigger a Response** | Turn digital activity into organizational or physical action: guards investigate, drones deploy, doors lock, administrators intervene |
| **Collateral Effect** | The desired effect still happens, but creates an unintended secondary problem appropriate to the fiction |

## Spend 2 Fear

| Effect | Result |
|---|---|
| **Close the Route** | The current Access route becomes Closed. Existing Progress remains, but another path must be established |
| **Deploy Dangerous ICE** | Introduce a significant ICE threat or shift the intrusion into the Detailed Device Intrusion rules; usually appropriate for Hardened or Fortified systems |
| **Counter-Intrusion** | Defenders attack the Netrunner's deck, relay, identity, associates, access assets, or other connected infrastructure |
| **Major Security Response** | Trigger network-wide lockdown, law enforcement, a corporate response team, evacuation, or emergency control procedures |

Fear spent by the GM does not normally remove Progress already earned. Opposition makes completion harder by **changing the situation**, not by deleting successful actions.

# Device Intrusion

The following rules remain useful when hacking is focused on a **specific device** or when defeating its defenses is important enough to play out in detail.

## Device Hardening

Devices fall into two broad categories.

### Unhardened Devices

Most civilian technology is effectively unsecured. Default passwords, unpatched exploits, and weak encryption are commonplace. These systems pose minimal risk to a skilled hacker.

### Hardened Devices

Professionally secured assets include surveillance drones, automated turrets, corporate vaults, secure servers, contract-grade cyberware, and similar infrastructure.

Hardened devices may contain ICE:

- **Walls** — passive protections such as encryption layers, access gates, and authentication barriers.
- **Sentries** — active monitoring programs and countermeasures designed to detect, isolate, or retaliate against intruders.

Determining whether a device is hardened requires a **Hacking: Analyze** action when that information is not already apparent from the fiction.

## Unhardened Devices

### Immediate Access

A hacker automatically gains **Control** over any unhardened device of their Tier when they have a usable route to it.

### Higher-Tier Devices

To control an unhardened device above their Tier, a hacker may **Mark 1 Stress** and make a **Hacking roll** against a Difficulty that scales with the device's Tier.

On a success, they gain Control.

Unhardened devices do not normally contain ICE or raise an alert on failure unless the fiction demands it.

## Hardened Devices

Use the detailed intrusion rules when the act of defeating the system is itself part of the dramatic challenge.

Hackers rely on three core actions.

### Analyze

Probe the system to understand its structure.

On a success, learn:

- Device Tier;
- ICE types present, including Walls and Sentries;
- ICE Tiers;
- one meaningful narrative detail.

Analyze is lower risk than overt intrusion, but active Sentries may still notice persistent probing.

### Infiltrate

Slip past ICE or operate within its blind spots.

Infiltrate establishes a deeper foothold than Analyze while prioritizing stealth and persistence. Use it when clean extraction, covert access, or remaining unnoticed matters more than immediate control.

### Control

Execute an overt intrusion using exploits, injections, recursion traps, destructive techniques, or other forceful methods.

Control grants the broadest authority over the device but is the most likely to provoke active defenses.

Use Control when speed, disruption, or domination matters more than subtlety.

## Alert, Exposure, and ICE

Some Device and ICE features use a **System Alert** level. When they do, track System Alert as written by those features.

System Alert and Network Action **Exposure** describe related but different scales:

- **System Alert** is the immediate awareness and defensive posture of a specific Device Intrusion encounter.
- **Exposure** tracks the broader consequences of an intrusion and how well defenders can identify or retaliate against its source.

When play moves between Network Actions and Detailed Device Intrusion, translate between them according to the fiction rather than treating them as automatically identical tracks.

## Range and Position

Network Actions are not limited by physical combat range. If a plausible network route exists, remote hacking is viable.

For **tactical Device Intrusion**, the GM may use normal combat range bands when signal strength, interference, line-of-sight networking, or physical proximity meaningfully matters to the scene.

An Isolated system still requires a local or physical foothold before any remote action can target it.

# Quick Reference

1. **Declare** the concrete outcome and plausible digital method.
2. **Establish Access.** If the target is Isolated, create a foothold first.
3. **Rate Security.** Security sets the Base Difficulty.
4. **Roll Hacking** against **Security Base + Access Modifier**.
5. **Build Progress.** P1/P2/P3/P4 require **1/2/3/5** successful Network Actions.
6. **Track Time** independently as Immediate, Short, Extended, or Strategic.
7. **Resolve Fear and failure.** Consequences change Exposure, Access, Security, Time, or the fiction.
8. **Zoom in when needed.** Use Analyze, Infiltrate, Control, and ICE when the intrusion itself becomes an encounter.
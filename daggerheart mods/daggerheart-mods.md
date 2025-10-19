In order for the Cybermancy new Domains to appear, requires 2 small changes to Daggerheart files:

/lang/en.json

				"hack": {
                    "label": "Hack",
                    "description": "This is the domain of the Matrix.  Those who chose this domain surf the digital spaces that overlay and often control the physical world.  They use their digital mastery to control the battlefield, disable their enhanced opponents, and lay waste to the corporate data fortresses."
                }

Added to the Domain list at line 1757

/build/daggerheart.js

    hack: {
        id: 'hack',
        label: 'DAGGERHEART.GENERAL.Domain.hack.label',
        src: 'modules/cybermancy/assets/icons/domains/hack.svg',
        description: 'DAGGERHEART.GENERAL.Domain.hack.description'
    }

Added to the Domain list at line 720
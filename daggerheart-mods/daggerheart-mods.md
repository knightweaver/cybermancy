In order for the Cybermancy new Domains to appear, requires 2 small changes to Daggerheart files:

/lang/en.json

				"circuit": {
                    "label": "Circuit",
                    "description": "This is the domain of the Matrix.  Those who chose this domain surf the digital spaces that overlay and often control the physical world.  They use their digital mastery to control the battlefield, disable their enhanced opponents, and lay waste to the corporate data fortresses."
                },
				"maker": {
                    "label": "Maker",
                    "description": "This is the domain of the Makers."
                },
				"bullet": {
                    "label": "Bullet",
                    "description": "This is the domain of those that shoot bullets."
                }

Added to the Domain list at line 1757

/build/daggerheart.js

    circuit: {
        id: 'circuit',
        label: 'DAGGERHEART.GENERAL.Domain.circuit.label',
        src: 'modules/cybermancy/assets/icons/domains/circuit.svg',
        description: 'DAGGERHEART.GENERAL.Domain.circuit.description'
    },
    maker: {
        id: 'maker',
        label: 'DAGGERHEART.GENERAL.Domain.maker.label',
        src: 'modules/cybermancy/assets/icons/domains/maker.svg',
        description: 'DAGGERHEART.GENERAL.Domain.maker.description'
    },
    bullet: {
        id: 'bullet',
        label: 'DAGGERHEART.GENERAL.Domain.bullet.label',
        src: 'modules/cybermancy/assets/icons/domains/bullet.svg',
        description: 'DAGGERHEART.GENERAL.Domain.bullet.description'
    }

Added to the Domain list at line 720
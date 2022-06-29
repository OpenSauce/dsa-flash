import { arrayBuffer } from "stream/consumers";

class FlashCardSet {
    cards: FlashCard[]
    name: string

    constructor(name: string, cards: FlashCard[]) {
        this.name = name;
        this.cards = cards;
    }
}

var flashCardSet: FlashCardSet[]

export function GetFlashCardSet() {
    if (!flashCardSet.length) {
        populateData()
    }

    return new FlashCard();
}

function populateData() {

}

class FlashCard {
    title = "";
    front = "";
    back = "";

    constructor() {
    }
}

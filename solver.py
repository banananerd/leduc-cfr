cards = [i for i in range(6)]
configNoBets = 2
class State:
    def copy(state):
        newState = State()
        newState.player = state.player
        newState.lastToAct = state.lastToAct
        newState.board = state.board
        newState.prevAction = state.prevAction
        newState.numberOfBets = state.numberOfBets
        newState.contributions = list(state.contributions)
        return newState
    
    def __init__(self):
        self.player = ''
        self.lastToAct = None
        self.board = None
        self.prevAction = None
        self.numberOfBets = None
        self.contributions = []
        return

class actionNode:
    def __init__(self, childNodes: list[object], regrets: dict[str, float], strategy_sum: dict[str, float], actions: list[str], player: int, board: list[int], pot: int):
        self.childNodes = childNodes
        self.regrets = regrets
        self.strategy_sum = strategy_sum
        self.actions = actions
        self.player = player
        self.board = board
        self.pot = pot

class chanceNode:
    def __init__(self, childNodes: list[actionNode]):
        self.childNodes = childNodes
        return
class terminalNode:
    def __init__(self, terminalKind, playerWhoFolded, contributions, board):
        self.terminalKind = terminalKind
        self.playerWhoFolded = playerWhoFolded
        self.contributions = contributions
        self.board = board
        return


#build game tree
def getLegalActions(state): # assumes terminal and chance conditions have been checked
    legalActions = []
    if not state.prevAction or state.prevAction == 'call' or state.prevAction == 'check': #closed action or checks to you
        legalActions = ['bet', 'check']
    elif state.prevAction in ['bet', 'raise']:
        if state.numberOfBets >= configNoBets: 
            legalActions = ['call', 'fold']
        else:
            legalActions = ['raise', 'call', 'fold']
    return legalActions

def deal(state, card):
    newState = State.copy(state)
    newState.board = card
    newState.lastToAct = None
    newState.player = 'p0'
    newState.prevAction = None
    newState.numberOfBets = 0
    return newState
def apply(action, state):
    newState = State.copy(state)
    newState.prevAction = action
    newState.lastToAct = state.player
    newState.player = 'p1' if state.player == 'p0' else 'p0'
    newState.numberOfBets = state.numberOfBets if action not in ['bet', 'raise'] else state.numberOfBets+1
    size = 4 if state.board is not None else 2

    opp = 1 - int(newState.lastToAct[1])

    if action in ['bet', 'raise']:
        newState.contributions[int(newState.lastToAct[1])] = newState.contributions[opp] + size
    elif action == 'call': 
        newState.contributions[int(newState.lastToAct[1])] = newState.contributions[opp]
    return newState
    
def build(state):
    if state.prevAction == 'fold':
        return terminalNode('fold', state.lastToAct, state.contributions, state.board) #with fold kind, pot board, player
    elif (state.prevAction == 'call' or (state.prevAction == 'check' and state.lastToAct == 'p1')) and state.board is not None:
        return terminalNode('showdown', None, state.contributions, state.board) # with fold kind, pot board, player
    elif (state.prevAction == 'check' and state.lastToAct == 'p1' or state.prevAction == 'call') and state.board is None:
        chance = chanceNode([])
        for card in range(6): 
            #add the card to the board state
            chance.childNodes.append(build(deal(state, card)))
        return chance
    #action node
    actNode = actionNode([], {}, {}, [], int(state.player[1]), state.board, sum(state.contributions))

    #conditions to figure out new state, then for each one append it to actionNode
    # player can bet, check, fold, or raise? depending on previous action
    for action in getLegalActions(state):        
        actNode.actions.append(action)
        actNode.childNodes.append(build(apply(action, state)))

    for action in actNode.actions:
        actNode.regrets[action] = [0.0] * (6)
        actNode.strategy_sum[action] = [0.0] * (6)
    return actNode


root = State()
root.numberOfBets = 0 
root.contributions = [1, 1]
root.player = 'p0'
root = build(root)


#for cfr, what do we need. we need to iterate through the tree, and update the regrets, strategy, and strategy sum as we go through the tree
# we can either encounter a chance node, action node, or terminal node
# at a terminal node, we return the payout
# at action node, we iterate through the actions and update the arrs based on returned payout
# at chance node, we iterate through each card? 
# need to pass curNode, player, reach\

#cfr function description
#if terminal node: 
#     return payout based on player and contributions. must multiply by how often opp gets there and weigh accordingly
# if action node :
#     call the recursive function for each action in its childNodes
#     update the regrets, and add to strategy sum accordingly after recursive call is returned

# if chance node: 
#     iterate through each card that the board plays out. msut zero that card out for players reach list
#     also multiply the reach by 1/4 because there are 4 possible board cards

#           J, J, Q, Q, K, K         
#hands are [0, 1, 2, 3, 4, 5]
def showdown(hand0, hand1, board):
    normHand0, normHand1 = hand0 // 2, hand1 // 2
    normBoard = board // 2 if board is not None else None
    if board is not None and normHand0 == normBoard:
        return 1
    elif board is not None and normHand1 == normBoard: 
        return -1
    elif (normHand0) > (normHand1):
        return 1
    elif (normHand0) < (normHand1):
        return -1
    else:
        return 0

def cfr(curNode, player, myReach, oppReach):
    playerNo = int(player[1])
    if isinstance(curNode, terminalNode):
        values = [0.0] * 6
        for myHand in range(6):
            if myHand == curNode.board:
                continue
            for oppHand in range(6):
                if oppHand == myHand or oppHand == curNode.board:
                    continue
                addedValue = None
                if curNode.playerWhoFolded is None:
                    addedValue = oppReach[oppHand] * showdown(myHand, oppHand, curNode.board) * curNode.contributions[playerNo^1]
                else:
                    folded = int(curNode.playerWhoFolded[1])
                    isWinning = -1 if playerNo == folded else 1
                    potSize = curNode.contributions[folded]
                    addedValue = oppReach[oppHand] * isWinning * potSize
                values[myHand] += addedValue
        return values    
    elif isinstance(curNode, chanceNode):
        # there are many actions possibly for each board card
        values = [0.0] * 6
        for card, child in enumerate(curNode.childNodes):
            newMyReach = list(myReach)
            newOppReach = [r*0.25 for r in oppReach]
            newMyReach[child.board] = 0
            newOppReach[child.board] = 0
            addToValues = cfr(child, player, newMyReach, newOppReach)
            for j in range(len(values)):
                values[j] += addToValues[j]
        return values
    elif isinstance(curNode, actionNode):
        # here we want to do some things
        # first normalize strategy, after CFR update regrets, add to strategy sum
        # how do we use strategy? we multiply our reach by the normalized strategy
        # self.childNodes = childNodes
        # self.regrets = regrets
        # self.strategy_sum = strategy_sum
        # self.actions = actions
        # self.player = player
        # self.board = board
        # self.pot = pot
        strategy = {}
        if curNode.actions:
            for action in curNode.actions:
                strategy[action] = [r if r > 0 else 0 for r in curNode.regrets[action]] 
        mixes = [[0]*len(curNode.actions) for i in range(6)]
        for action, handValues in strategy.items():
            for i, handValue in enumerate(handValues):
                mixes[i][curNode.actions.index(action)] += handValue
        for k, handMixes in enumerate(mixes):
            s = sum(handMixes)
            mixes[k] = [handMixes[i] / s if s else 1/len(handMixes) for i in range(len(handMixes))]



        # IF OPPONENT
        # you want to use their strategy, and calculate your EV based on their strategy. so to do that pass
        # the correct reach based on their action for each hand. and calculate each of our Hand EVs based on that, and pass that val.
        if playerNo != curNode.player:
            oppNodeOurValues = [0.0] * 6
            for j in range(len(curNode.actions)):
                newOppReach = [oppReach[h] * mixes[h][j] for h in range(6)]
                for i, handVal in enumerate(cfr(curNode.childNodes[j], player, myReach, newOppReach)):
                    oppNodeOurValues[i] += handVal
            return oppNodeOurValues


        pureEVs = [[0]*len(curNode.actions) for i in range(6)]


        mixedEVs = [0.0]*6
        for action, child in zip(curNode.actions, curNode.childNodes):
            newMyReach = [mixes[i][curNode.actions.index(action)] * myReach[i] for i in range(len(myReach))]
            #get EV for each action for each hand, so those are the pure EVs? 
            pureEV = cfr(child, player, newMyReach, oppReach)
            for i, handEV in enumerate(pureEV):
                pureEVs[i][curNode.actions.index(action)] = pureEV[i]
                mixedEVs[i] += mixes[i][curNode.actions.index(action)] * pureEV[i]

        for i in range(6):
            for j in range(len(pureEVs[i])):
                curNode.regrets[curNode.actions[j]][i] += pureEVs[i][j]-mixedEVs[i]
                curNode.strategy_sum[curNode.actions[j]][i] += mixes[i][j] * myReach[i]
        return mixedEVs
    

# run cfr, converge to NE 
for i in range(1000):
    cfr(root, 'p0', [1.0 for i in range(6)], [1.0 for i in range(6)])
    cfr(root, 'p1', [1.0 for i in range(6)], [1.0 for i in range(6)])
    
# test exploitability
# want to freeze strategy for a player, then run the CFR algo but with best pure action to see how exploitable the opp strategy is 

# testing how exploitable opponent strategy is
# go through the tree, pick the pure actions that get Best EV for each hand, and freeze opponent strategy. 
# see EV for each hand at end

def exploitability(curNode, player, oppReach):
    playerNo = int(player[1])
    if isinstance(curNode, terminalNode):
        values = [0.0] * 6
        for myHand in range(6):
            if myHand == curNode.board:
                continue
            for oppHand in range(6):
                if oppHand == myHand or oppHand == curNode.board:
                    continue
                addedValue = None
                if curNode.playerWhoFolded is None:
                    addedValue = oppReach[oppHand] * showdown(myHand, oppHand, curNode.board) * curNode.contributions[playerNo^1]
                else:
                    folded = int(curNode.playerWhoFolded[1])
                    isWinning = -1 if playerNo == folded else 1
                    potSize = curNode.contributions[folded]
                    addedValue = oppReach[oppHand] * isWinning * potSize
                values[myHand] += addedValue
        return values    
    elif isinstance(curNode, chanceNode):
        # there are many actions possibly for each board card
        values = [0.0] * 6
        for card, child in enumerate(curNode.childNodes):
            newOppReach = [r*0.25 for r in oppReach]
            newOppReach[child.board] = 0
            addToValues = exploitability(child, player, newOppReach)
            for j in range(len(values)):
                values[j] += addToValues[j]
        return values
    elif isinstance(curNode, actionNode):
            mixes = [[0]*len(curNode.actions) for i in range(6)]
            for action, handValues in curNode.strategy_sum.items():
                for i, handValue in enumerate(handValues):
                    mixes[i][curNode.actions.index(action)] += handValue
            for k, handMixes in enumerate(mixes):
                s = sum(handMixes)
                mixes[k] = [handMixes[i] / s if s else 1/len(handMixes) for i in range(len(handMixes))]
    
    
            if playerNo != curNode.player:
                oppNodeOurValues = [0.0] * 6
                for j in range(len(curNode.actions)):
                    newOppReach = [oppReach[h] * mixes[h][j] for h in range(6)]
                    for i, handVal in enumerate(exploitability(curNode.childNodes[j], player, newOppReach)):
                        oppNodeOurValues[i] += handVal
                return oppNodeOurValues
            
            pureEVs = [[0]*len(curNode.actions) for i in range(6)]


            for action, child in zip(curNode.actions, curNode.childNodes):
                #get EV for each action for each hand, so those are the pure EVs? 
                pureEV = exploitability(child, player, oppReach)
                for i, handEV in enumerate(pureEV):
                    pureEVs[i][curNode.actions.index(action)] = pureEV[i]

            handMaxEvs = [0.0] * 6
            for i in range(6):
                handMaxEvs[i] = max(pureEVs[i])
            return handMaxEvs
p0Exploitability = exploitability(root, 'p1', [1.0 for i in range(6)])
p1Exploitability = exploitability(root, 'p0', [1.0 for i in range(6)])
print("EV loss based on current strategy for p1: ", sum(p1Exploitability)/30)
print("EV loss based on current strategy for p0: ", sum(p0Exploitability)/30)
print("Game EV Loss", (sum(p1Exploitability) + sum(p0Exploitability)) / 30)



        
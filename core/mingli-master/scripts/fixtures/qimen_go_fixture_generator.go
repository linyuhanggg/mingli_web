// Frozen extraction helper for the pinned qimen-go engineering comparison.
// Run inside checkout 4d3f58fa0f401b5b3a337f119138e99e90685dda as cmd/qimenjson/main.go.
package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/deminzhang/qimen-go/util"
	"github.com/deminzhang/qimen-go/xuan"
)

type palace struct {
	Palace int    `json:"palace"`
	Earth  string `json:"earth"`
	Heaven string `json:"heaven"`
	Star   string `json:"star"`
	Door   string `json:"door"`
	Deity  string `json:"deity"`
}

type result struct {
	Datetime                  string   `json:"datetime"`
	Term                      string   `json:"term"`
	Day                       string   `json:"day"`
	Hour                      string   `json:"hour"`
	Yuan                      int      `json:"yuan"`
	Ju                        int      `json:"ju"`
	Xun                       string   `json:"xun"`
	Void                      string   `json:"void"`
	Horse                     string   `json:"horse"`
	Chief                     string   `json:"chief"`
	ChiefPalace               int      `json:"chief_palace"`
	Director                  string   `json:"director"`
	DirectorPalace            int      `json:"director_palace"`
	CenterHosting             int      `json:"center_hosting"`
	CompatibleSignatureSHA256 string   `json:"compatible_signature_sha256"`
	RawProjection             []palace `json:"raw_projection"`
}

func main() {
	results := make([]result, 0, len(os.Args)-1)
	for _, supplied := range os.Args[1:] {
		solar, err := util.ParseTime(supplied)
		if err != nil {
			panic(err)
		}
		game := xuan.NewQMGame(solar, xuan.QMParams{
			Type:        xuan.QMTypeRotating,
			HostingType: xuan.QMHostingType2,
			FlyType:     xuan.QMFlyTypeAllOrder,
			JuType:      xuan.QMJuTypeSplit,
			HideGanType: xuan.QMHideGanDutyDoorHour,
			YMDH:        xuan.QMGameHour,
		})
		pan := game.TimePan
		row := result{
			Datetime: supplied, Term: game.JieQi,
			Day:  game.Lunar.GetDayInGanZhiExact(),
			Hour: game.Lunar.GetTimeInGanZhi(),
			Yuan: pan.Yuan3, Ju: pan.Ju, Xun: pan.Xun,
			Void: pan.KongWang, Horse: pan.Horse,
			Chief: pan.DutyStar, ChiefPalace: pan.DutyStarPos,
			Director: pan.DutyDoor, DirectorPalace: pan.DutyDoorPos,
			CenterHosting: pan.RollHosting,
		}
		var compatible strings.Builder
		for palaceNumber := 1; palaceNumber <= 9; palaceNumber++ {
			gong := pan.Gongs[palaceNumber]
			row.RawProjection = append(row.RawProjection, palace{
				Palace: palaceNumber, Earth: gong.HostGan,
				Heaven: gong.GuestGan, Star: gong.Star,
				Door: gong.Door, Deity: gong.God,
			})
			if palaceNumber > 1 {
				compatible.WriteString("|")
			}
			if palaceNumber == 5 {
				compatible.WriteString(fmt.Sprintf("5:%s/-/-/-/-", gong.HostGan))
			} else {
				compatible.WriteString(fmt.Sprintf(
					"%d:%s/%s/%s/%s/%s", palaceNumber, gong.HostGan,
					gong.GuestGan, gong.Star, gong.Door, gong.God,
				))
			}
		}
		row.CompatibleSignatureSHA256 = fmt.Sprintf(
			"%x", sha256.Sum256([]byte(compatible.String())),
		)
		results = append(results, row)
	}
	encoded, err := json.Marshal(results)
	if err != nil {
		panic(err)
	}
	fmt.Println(string(encoded))
}
